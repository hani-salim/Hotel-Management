from odoo import models, fields


class LoyaltyReward(models.Model):
    _name = 'loyalty.reward'
    _description = 'Loyalty Reward'

    name = fields.Char(string="Reward Name", required=True)
    active = fields.Boolean(string="Active", default=True)
    reward_type = fields.Selection([
        ('discount', 'Discount'),
        ('free_night', 'Free night'),
        ('service', 'Free Service')
    ], string="Type Reward", default='discount', required=True)

    discount_percent = fields.Float(string="Discount %", default=10.0)
    points_cost = fields.Integer(string="Cost Points", default=100)