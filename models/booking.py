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
    room_ids = fields.Many2many('hotel.room', 'booking_ids', string='Room',
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
    branch_id = fields.Many2one('hotel.branch', string="Branch")
    user_id = fields.Many2one('res.users', string="Created By", default=lambda self: self.env.user.id)
    user_center = fields.Boolean(
        compute='_compute_user_center',
        search='_search_user_center',
    )
    user_filter = fields.Char(string="User Domain Filter")
    show_button = fields.Boolean(compute='_compute_show_button', default=True)
    available_room_ids = fields.Many2many(
        'hotel.room',
        string="Available Rooms"
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

                for room in booking.room_ids:
                    if not room.is_available:
                        raise UserError(_("الغرف مشغولة حاليا يرجى إعادة تاكيد الطلب لاحقا !"))

                invoice = self.env['account.move'].search([
                    ('partner_id', '=', booking.guest_id.partner_id.id),
                    ('payment_state', '!=', 'paid'),
                    ('guest_id', '=', booking.guest_id.id),
                ], limit=1)

                if 1:
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
                            'room_id': room.id,
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
                        booking.invoice_id = invoice.id

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
            try:
                print(' i am in action cancel')
                if booking.invoice_id:
                    print('booking has invoice id')
                    invoice_lines_to_remove = booking.invoice_id.invoice_line_ids.filtered(
                        lambda l: l.room_id and l.room_id.id in booking.room_ids.ids
                    )
                    print('invoice_lines_to_remove : ', invoice_lines_to_remove)

                    if invoice_lines_to_remove:
                        invoice_lines_to_remove.unlink()

                        if not booking.invoice_id.invoice_line_ids:
                            booking.invoice_id.button_cancel()

                    else:
                        booking.invoice_id.button_cancel()
                else:
                    raise UserError('no invoice related in this booking')

                if booking.room_ids:
                    booking.room_ids.write({
                        'current_guest_id': False,
                        'state': 'ready'
                    })

                booking.state = 'cancel'
                booking.invoice_id = False

            except Exception as e:
                _logger.error("Failed to cancel booking %s: %s", booking.id, str(e))
                raise UserError(_("Failed to cancel booking: %s") % str(e))

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

    def _compute_user_center(self):
        current_user = self.env.user
        for booking in self:
            booking.user_center = bool(
                booking.user_id.id == current_user.id
                or current_user.has_group('hotel.group_hotel_manager')
                or current_user.has_group('hotel.group_hotel_user')
                or (
                        current_user.has_group('hotel.group_hotel_branch_manager') and
                        booking.branch_id.manager_id.user_id.id == current_user.id
                )
            )

    def _search_user_center(self, operator, value):
        current_user = self.env.user

        current_employee = self.env['hr.employee'].search([
            ('user_id', '=', current_user.id),
            ('company_id', '=', current_user.company_id.id)
        ], limit=1)

        if current_user.has_group('hotel.group_hotel_manager'):
            allowed_ids = self.search([]).ids

        else:
            allowed_ids = self.search([('user_id', '=', current_user.id)]).ids

        if operator == '=' and value:
            print(allowed_ids)
            return [('id', 'in', allowed_ids)]
        elif operator == '!=' and not value:
            return [('id', 'not in', allowed_ids)]
        else:
            return []
