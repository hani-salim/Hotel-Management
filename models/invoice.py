from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountMoveInherit(models.Model):
    _inherit = 'account.move'

    booking_ids = fields.One2many('hotel.booking','invoice_id',compute='_compute_fields', string='Booking')
    guest_id = fields.Many2one('hotel.guest', string='Guest', store=True)
    is_hotel_invoice = fields.Boolean(string='Hotel Invoice', default=False)
    room_ids = fields.Many2many(
        'hotel.room',
        string='Rooms',
        compute='_compute_fields',
        tracking=True
    )



    @api.depends('guest_id','guest_id.booking_ids','guest_id.room_ids')
    def _compute_fields(self):
        for invoice in self:
            invoice.booking_ids = invoice.guest_id.booking_ids
            invoice.room_ids = invoice.guest_id.room_ids
