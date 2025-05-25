# sale_order.py
from odoo import models, fields

class SaleOrderInherit(models.Model):
    _inherit = 'sale.order'

    loyalty_discount = fields.Float(string="Loyalty Discount")
    loyalty_reward_id = fields.Many2one('loyalty.reward', string="Loyalty Reward")
    loyalty_points_used = fields.Integer(string="Points Used")
    guest_id = fields.Many2one('hotel.guest', string="Guest")