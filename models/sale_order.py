from odoo import models, fields, api
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    guest_id = fields.Many2one('hotel.guest', string='Guest', store=True)
