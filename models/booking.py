from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)


class HotelBooking(models.Model):
    _name = 'hotel.booking'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Booking Request'

    guest_id = fields.Many2one('hotel.guest', string='Guest', required=True)
    room_ids = fields.Many2many('hotel.room', 'booking_ids', string='Room', domain="[('is_available', '=', True)]",
                                required=True)
    check_in_date = fields.Datetime(string='Check-in Date', default=fields.Datetime.now, required=True)
    check_out_date = fields.Datetime(string='Check-out Date', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirm'),
        ('done', 'Done'),
        ('cancel', 'Cancel')
    ], string='Status', default='draft', tracking=True)
    invoice_id = fields.Many2one('account.move', string='Invoice')
    payment_state = fields.Selection(related='invoice_id.payment_state', string='Payment Status')
    duration = fields.Integer(string='Duration (Days)', compute='_compute_duration', store=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
        readonly=True
    )

    @api.depends('check_in_date', 'check_out_date')
    def _compute_duration(self):
        for guest in self:
            if guest.check_in_date and guest.check_out_date:
                delta = guest.check_out_date - guest.check_in_date
                guest.duration = delta.days
            else:
                guest.duration = 0

    @api.model
    def get_available_rooms(self, check_in, check_out):

        if isinstance(check_in, str):
            check_in = fields.Date.from_string(check_in)
        if isinstance(check_out, str):
            check_out = fields.Date.from_string(check_out)

        conflicting_bookings = self.search([
            ('state', 'not in', ['cancel', 'done']),
            '|',
            '&',
            ('check_in_date', '<', check_out),
            ('check_out_date', '>', check_in),
            '&',
            ('check_in_date', '>=', check_in),
            ('check_out_date', '<=', check_out)
        ])

        booked_room_ids = conflicting_bookings.mapped('room_ids').ids
        print(booked_room_ids)

        available_rooms = self.env['hotel.room'].search([
            ('id', 'not in', booked_room_ids),
            ('state', '!=', 'out_of_service'),
        ])


        return available_rooms

    def action_confirm(self):
        for booking in self:
            try:
                if not booking.guest_id:
                    raise UserError(_("يجب تحديد ضيف للحجز!"))

                if not booking.room_ids:
                    raise UserError(_("يجب تحديد غرفة واحدة على الأقل!"))

                # التحقق من وجود فاتورة نشطة للضيف
                invoice = self.env['account.move'].search([
                    ('partner_id', '=', booking.guest_id.partner_id.id),
                    ('payment_state', '!=', 'paid'),
                    ('guest_id', '=', booking.guest_id.id),
                ], limit=1)

                if 1:
                    # إنشاء فاتورة جديدة إذا لم توجد
                    invoice_line_vals_list = []

                    for room in booking.room_ids:
                        if not room.product_id:
                            raise UserError(_("لم يتم تعيين منتج للغرفة {}!".format(room.name)))

                        product = room.product_id
                        duration = (booking.check_out_date - booking.check_in_date).days

                        if duration <= 0:
                            raise UserError(_("مدة الإقامة يجب أن تكون يومًا واحدًا على الأقل!"))

                        account = product.property_account_income_id or \
                                  product.categ_id.property_account_income_categ_id

                        if not account:
                            raise UserError(_("لم يتم تعيين حساب إيرادات للمنتج أو فئة المنتج!"))

                        invoice_line_vals = {
                            'product_id': product.id,
                            'name': f"إقامة في غرفة {room.name} ({duration} أيام)",
                            'quantity': duration,
                            'product_uom_id': product.uom_id.id,
                            'price_unit': room.price_per_night,
                            'account_id': account.id,
                            'tax_ids': [(6, 0, product.taxes_id.ids)] if product.taxes_id else False,
                        }
                        invoice_line_vals_list.append((0, 0, invoice_line_vals))

                    journal = self.env['account.journal'].search([
                        ('type', '=', 'sale'),
                        ('company_id', '=', booking.company_id.id)
                    ], limit=1)

                    if not journal:
                        raise UserError(_("لم يتم العثور على دفتر يومية مبيعات!"))

                    due_date = fields.Date.today() + timedelta(days=7)

                    invoice_vals = {
                        'move_type': 'out_invoice',
                        'partner_id': booking.guest_id.partner_id.id,
                        'invoice_date': fields.Date.today(),
                        'invoice_date_due': due_date,
                        'journal_id': journal.id,
                        'invoice_line_ids': invoice_line_vals_list,
                        'company_id': booking.company_id.id,
                        'currency_id': booking.company_id.currency_id.id,
                        'guest_id': booking.guest_id.id,
                    }

                    if not invoice:
                        invoice = self.env['account.move'].create(invoice_vals)
                        booking.invoice_id = invoice.id
                    else:
                        invoice.write({
                            'invoice_line_ids': invoice_line_vals_list,
                        })

                # تحديث حالة الغرف
                booking.room_ids.write({
                    'current_guest_id': booking.guest_id.id,
                    'state': 'booking'
                })

                booking.state = 'confirm'

                points = self.duration * 10
                self.guest_id.sudo().write({
                    'loyalty_points': self.guest_id.loyalty_points + points
                })

                return {
                    'name': _('Invoice'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'account.move',
                    'res_id': invoice.id,
                    'view_mode': 'form',
                    'target': 'current',
                }

            except Exception as e:
                _logger.error("فشل تأكيد الحجز %s: %s", booking.id, str(e), exc_info=True)
                raise UserError(_("فشل في تأكيد الحجز: %s") % str(e))

    def action_cancel(self):
        for booking in self:
            if booking.invoice_id:
                booking.invoice_id.button_cancel()

            if booking.room_ids:
                booking.room_ids.write({
                    'current_guest_id': False,
                    'state': 'ready'
                })

            booking.state = 'cancel'

    @api.constrains('check_in_date', 'check_out_date')
    def _check_dates(self):
        for booking in self:
            if booking.check_out_date <= booking.check_in_date:
                raise UserError(_("Check-out date must be after check-in date"))

    @api.model
    def _valid_field_parameter(self, field, name):
        return name == 'tracking' or super()._valid_field_parameter(field, name)

    def clean_cancelled_bookings(self):
        cancelled_bookings = self.search([
            ('state', '=', 'cancelled'),
            ('create_date', '<', fields.Datetime.now() - timedelta(days=30))
        ])
        cancelled_bookings.unlink()
