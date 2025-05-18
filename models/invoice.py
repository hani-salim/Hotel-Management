# invoice.py
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AccountMoveInherit(models.Model):
    _inherit = 'account.move'

    booking_ids = fields.One2many('hotel.booking', 'invoice_id', compute='_compute_fields', string='Booking')
    guest_id = fields.Many2one('hotel.guest', string='Guest', store=True)
    is_hotel_invoice = fields.Boolean(string='Hotel Invoice', default=False)
    room_ids = fields.Many2many('hotel.room', string='Rooms', compute='_compute_fields', tracking=True)
    loyalty_discount = fields.Float(string="Loyalty Discount")
    loyalty_reward_id = fields.Many2one('loyalty.reward', string="Loyalty Reward")
    loyalty_points_used = fields.Integer(string="Points Used")

    @api.model
    def create(self, vals):
        invoice = super().create(vals)

        # إذا كانت الفاتورة من أمر بيع، ننسخ خصومات العناصر
        if invoice.invoice_origin:
            sale_order = self.env['sale.order'].search([('name', '=', invoice.invoice_origin)], limit=1)
            if sale_order:
                for line in invoice.invoice_line_ids:
                    sale_line = sale_order.order_line.filtered(
                        lambda l: l.product_id == line.product_id
                    )
                    if sale_line:
                        line.discount = sale_line.discount
        return invoice


    @api.depends('guest_id', 'guest_id.booking_ids', 'guest_id.room_ids')
    def _compute_fields(self):
        for invoice in self:
            invoice.booking_ids = invoice.guest_id.booking_ids
            invoice.room_ids = invoice.guest_id.room_ids