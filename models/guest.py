from datetime import timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class HotelGuest(models.Model):
    _name = 'hotel.guest'
    _description = 'Hotel Guest'
    _rec_name = 'partner_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    partner_id = fields.Many2one('res.partner', required=1)
    id_number = fields.Char(string='ID/Passport Number', tracking=True)
    membership_type = fields.Selection([
        ('regular', 'Regular'),
        ('vip', 'VIP')
    ], string='Membership Type', default='regular', tracking=True)
    notes = fields.Text(string='Notes')
    room_ids = fields.One2many('hotel.room','current_guest_id', string='Current Room', tracking=True)
    duration = fields.Integer(string='Duration (Days)', compute='_compute_duration', store=True)
    review_ids = fields.One2many('hotel.review', 'guest_id', string='Reviews')
    invoice_count = fields.Integer(string='Invoice Count', compute='_compute_invoice_count')
    invoice_ids = fields.Many2many('account.move', 'guest_id', string='Invoices')
    booking_ids = fields.One2many('hotel.booking', 'guest_id', string='Booking List')
    stage = fields.Selection([
        ('1', 'Personal Information'),
        ('2', 'Room Selection')
    ], string='Registration Stage', default='1')
    check_in_date = fields.Datetime(string='Check-in Date', default=fields.Datetime.now, required=True)
    check_out_date = fields.Datetime(string='Check-out Date')
    service_request_ids = fields.One2many('hotel.service.request','guest_id')
    loyalty_tier = fields.Selection(
        [('silver', 'Silver'), ('gold', 'Gold'), ('platinum', 'Platinum')],
        compute='_compute_loyalty_tier'
    )
    loyalty_points = fields.Integer(default=0, tracking=True)
    reward_ids = fields.Many2many('loyalty.reward', string="Eligible Rewards")
    transaction_ids = fields.One2many('loyalty.transaction', 'guest_id')

    def _update_eligible_rewards(self):
        for partner in self:
            partner.reward_ids = self.env['loyalty.reward'].search([
                ('points_cost', '<=', partner.loyalty_points),
                ('active', '=', True)
            ])

    @api.depends('loyalty_points')
    def _compute_loyalty_tier(self):
        for partner in self:
            if partner.loyalty_points >= 5000:
                partner.loyalty_tier = 'platinum'
            elif partner.loyalty_points >= 2000:
                partner.loyalty_tier = 'gold'
            else:
                partner.loyalty_tier = 'silver'

    @api.depends('check_in_date', 'check_out_date')
    def _compute_duration(self):
        for guest in self:
            if guest.check_in_date and guest.check_out_date:
                delta = guest.check_out_date - guest.check_in_date
                guest.duration = delta.days
            else:
                guest.duration = 0

    def action_next_stage(self):
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_("Partner is required!"))

        # البحث عن ضيف موجود بنفس partner_id
        existing_guest = self.env['hotel.guest'].search([
            ('partner_id', '=', self.partner_id.id),
            ('id', '!=', self.id)
        ], limit=1)

        if existing_guest:
            all_room_ids = existing_guest.room_ids.ids + self.room_ids.ids

            # تحديث بيانات الضيف الموجود
            existing_guest.write({
                'room_ids': [(6, 0, list(dict.fromkeys(all_room_ids)))],
                'check_in_date': min(existing_guest.check_in_date, self.check_in_date),
                'check_out_date': max(existing_guest.check_out_date or self.check_out_date,
                                      self.check_out_date or existing_guest.check_out_date),
                'notes': self.notes or existing_guest.notes,
                'membership_type': self.membership_type or existing_guest.membership_type,
                'id_number': self.id_number or existing_guest.id_number,
                'stage': '2'  # الانتقال للمرحلة الثانية
            })

            # حذف الضيف الجديد بعد دمج البيانات
            self.unlink()

            return {
                'type': 'ir.actions.act_window',
                'res_model': 'hotel.guest',
                'res_id': existing_guest.id,
                'view_mode': 'form',
                'target': 'new',
                'context': {'form_view_ref': 'hotel.view_guest_registration_form'}
            }

        # إذا لم يكن هناك ضيف موجود، الانتقال للمرحلة الثانية
        self.stage = '2'
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.guest',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {'form_view_ref': 'hotel.view_guest_registration_form'}
        }

    def action_submit_booking(self):
        if not self.check_out_date or self.check_out_date < fields.Datetime.now():
            raise UserError(_("Please select a valid check-out date!"))

        duration = (self.check_out_date - fields.Datetime.now()).days
        if duration <= 0:
            raise UserError(_("Duration must be at least 1 day!"))

        rooms = []
        for room in self.room_ids:
            if self.env['hotel.booking'].search([
                ('room_ids', 'in', room.id),
                ('state', '!=', 'done'),

            ]):
                pass
            else:
                rooms.append(room.id)

        if rooms:
            # Create booking
            booking = self.sudo().env['hotel.booking'].create({
                'guest_id': self.id,
                'room_ids': [(6, 0, rooms)],
                'check_in_date': fields.Datetime.now(),
                'check_out_date': self.check_out_date
            })
        else:
            raise UserError(_("Please select a room!"))


        self.room_ids.action_set_booking()

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.booking',
            'res_id': booking.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def _compute_invoice_count(self):
        for guest in self:
            guest.invoice_count = self.env['account.move'].search_count([
                ('guest_id', '=', guest.id)
            ])

    def action_redeem(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Redeem Reward',
            'res_model': 'loyalty.redeem.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_guest_id': self.id,
            }
        }



    def get_review_url(self):
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f"{base_url}/hotel/review/{self.id}"

    def send_checkout_reminder(self):
        """إرسال تذكير بالمغادرة للضيوف الذين يغادرون غداً"""
        tomorrow = fields.Date.today() + timedelta(days=1)
        guests = self.search([
            ('check_out_date', '=', tomorrow),
            ('email', '!=', False),
            ('room_id', '!=', False)
        ])

        template = self.env.ref('hotel.email_template_check_out_reminder')
        for guest in guests:
            try:
                template.send_mail(guest.id, force_send=True)
                _logger.info(f"Check-out reminder sent to {guest.name} ({guest.email})")
            except Exception as e:
                _logger.error(f"Failed to send check-out reminder to {guest.name}: {str(e)}")

    def send_review_requests(self):
        """إرسال طلبات التقييم للضيوف الذين غادروا بالأمس"""
        yesterday = fields.Date.today() - timedelta(days=1)
        guests = self.search([
            ('check_out_date', '=', yesterday),
            ('email', '!=', False)
        ])

        template = self.env.ref('hotel.email_template_review_request')
        for guest in guests:
            try:
                template.send_mail(guest.id, force_send=True)
                _logger.info(f"Review request sent to {guest.name} ({guest.email})")
            except Exception as e:
                _logger.error(f"Failed to send review request to {guest.name}: {str(e)}")


