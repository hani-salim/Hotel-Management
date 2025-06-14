from datetime import timedelta
from email.policy import default
from warnings import catch_warnings

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HotelRoom(models.Model):
    _name = 'hotel.room'
    _description = 'Hotel Room'

    name = fields.Char(string='Room Number', required=True)
    description = fields.Text(string='Description')
    floor = fields.Integer(string='Floor', required=1)
    view_type = fields.Selection([
        ('sea', 'Sea View'),
        ('city', 'City View'),
        ('garden', 'Garden View')
    ], string='View Type', default='sea', required=True)
    state = fields.Selection([
        ('ready', 'Ready'),
        ('needs_cleaning', 'Needs Cleaning'),
        ('needs_maintenance', 'Needs Maintenance'),
        ('out_of_service', 'Out of service'),
        ('booking', 'Booking'),
    ], string='Status', default='ready', required=1)
    current_guest_id = fields.Many2one('hotel.guest', string='Current Guest')
    booking_count = fields.Integer(string='Booking Count', compute='_compute_booking_count')
    booking_ids = fields.Many2many('hotel.booking', 'room_ids')
    is_available = fields.Boolean(string='Is Available', compute='_compute_availability', store=1, default=1)
    last_cleaning_date = fields.Datetime(string='Last Cleaning Date')
    last_maintenance_date = fields.Datetime(string='Last Maintenance Date')
    current_guest_invoice_id = fields.Many2one('account.move', string='Current Invoice')
    product_id = fields.Many2one(
        'product.product',
        string='Room Product',
        required=True,
        domain="[('is_room', '=', True)]"
    )
    price_per_night = fields.Float(
        string='Price Per Night',
        related='product_id.lst_price',
        store=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True
    )

    @api.depends('booking_ids')
    def _compute_booking_count(self):
        for room in self:
            room.booking_count = len(room.booking_ids)

    @api.depends('state', 'current_guest_id')
    def _compute_availability(self):
        for room in self:
            if room.state == 'ready' and not room.current_guest_id:
                room.is_available = True
            else:
                room.is_available = False

    def action_set_cleaning(self):
        self.write({'state': 'needs_cleaning'})

    def action_set_maintenance(self):
        self.write({'state': 'needs_maintenance'})

    def action_set_ready(self):
        self.write({'state': 'ready'})

    def action_set_booking(self):
        self.write({'state': 'booking'})

    def _update_room_states(self):
        rooms = self.search([])
        for room in rooms:
            if room.current_guest_id:
                # إذا مضى 24 ساعة من الإقامة، تحتاج الغرفة للتنظيف
                if fields.Datetime.now() > room.current_guest_id.check_in_date + timedelta(hours=24):
                    room.state = 'needs_cleaning'
            elif not room.current_guest_id and room.state == 'needs_cleaning':
                # إذا كانت الغرفة خالية وتحتاج تنظيف
                room.state = 'needs_maintenance'

    def action_open_booking(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'New Booking',
            'res_model': 'hotel.booking',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_room_ids': self.id}
        }

    def action_open_check_in_form(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.guest',
            'views': [(self.env.ref('hotel.view_guest_registration_form').id, 'form')],
            'target': 'new',
            'context': {
                'default_room_ids': [self.id],
            }
        }

    def action_open_check_out_form(self):
        if not self.current_guest_id:
            raise UserError("لا يوجد ضيف حالياً في هذه الغرفة")

        booking_id = self.env['hotel.booking'].sudo().search([
            ('guest_id', '=', self.current_guest_id.id),
            ('state', '=', 'draft'),
        ], limit=1)

        if booking_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'hotel.booking',
                'res_id': booking_id.id,
                'view_mode': 'tree',
                'target': 'new',
                'context': {}
            }

        # البحث عن الفاتورة المرتبطة بالضيف والغرفة
        invoice = self.env['account.move'].search([
            ('guest_id', '=', self.current_guest_id.id),
            ('room_ids', 'in', self.id),
        ], limit=1, order='create_date desc')

        if invoice:
            if invoice.payment_state == 'paid':
                current_date = fields.Datetime.now()
                print(current_date)
                booking = self.env['hotel.booking'].search([
                    ('room_ids', 'in', self.id),
                    ('guest_id', '=', self.current_guest_id.id),
                    ('state', '!=', 'done'),
                ], limit=1)
                check_out_date = booking.check_out_date if booking else self.current_guest_id.check_out_date
                print(check_out_date)

                if current_date < check_out_date:
                    raise UserError("Check out date is note today")
                else:
                    guest = self.current_guest_id

                    # 1. تحديث حالة الغرف
                    rooms_to_clean = guest.room_ids
                    rooms_to_clean.write({
                        'state': 'needs_cleaning',
                        'current_guest_id': False,
                        'current_guest_invoice_id': False
                    })

                    # 2. مسح بيانات الغرف من الضيف
                    guest.write({
                        'room_ids': [(5, 0, 0)],
                        'check_out_date': fields.Datetime.now(),
                        'booking_ids': [(5, 0, 0)],
                    })

                    # 3. تحديث الحجوزات المرتبطة
                    bookings = self.env['hotel.booking'].search([
                        ('guest_id', '=', guest.id),
                        ('state', '!=', 'done')
                    ])
                    bookings.write({'state': 'done'})

                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': 'تمت عملية الخروج بنجاح',
                            'message': 'تم تحديث حالة الغرف والحجوزات',
                            'type': 'success',
                            'sticky': False
                        }
                    }
            else:
                # فتح نموذج الفاتورة إذا لم تكن مدفوعة
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'account.move',
                    'res_id': invoice.id,
                    'views': [(False, 'form')],
                    'target': 'current',
                    'context': {
                        'form_view_initial_mode': 'edit',
                        'default_guest_id': self.current_guest_id.id,
                        'default_room_ids': self.id
                    }
                }
        else:
            booking = self.env['hotel.booking'].search([
                ('guest_id', '=', self.current_guest_id.id),
                ('room_ids', 'in', self.id),
                ('state', '!=', 'done')
            ], limit=1)

            if booking:
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'hotel.booking',
                    'res_id': invoice.id,
                    'views': [(False, 'form')],
                    'target': 'new',
                    'context': {
                        'form_view_initial_mode': 'edit',
                        'default_guest_id': self.current_guest_id.id,
                        'default_room_ids': self.id
                    }
                }
            else:
                raise UserError("لا يوجد فاتورة أو حجز نشط لهذا الضيف في هذه الغرفة")

    def action_check_availability(self):
        return {
            'name': _('Check Room Availability'),
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.room.availability.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_room_ids': self.ids},
        }

    def open_bookings_view(self):
        context = self.env.context
        available_room_ids = context.get('available_room_ids', False)
        room_ids = available_room_ids if available_room_ids else self.ids

        return {
            'type': 'ir.actions.act_window',
            'name': _('New Booking'),
            'res_model': 'hotel.booking',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_available_room_ids': [(6, 0, room_ids)],
                'default_check_in_date': context.get('default_check_in_date'),
                'default_check_out_date': context.get('default_check_out_date')
            }
        }
