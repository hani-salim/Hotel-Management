from odoo import models, fields, api

class LoyaltyTransaction(models.Model):
    _name = 'loyalty.transaction'
    _description = 'Loyalty Transaction'
    _order = 'date desc'

    guest_id = fields.Many2one('hotel.guest', required=True)
    points = fields.Integer(required=True)
    date = fields.Datetime(default=fields.Datetime.now)
    reference = fields.Reference([
        ('hotel.booking', 'Booking'),
        ('sale.order', 'Order'),
        ('account.move', 'Invoice')
    ])
    reward_id = fields.Many2one('loyalty.reward')
    transaction_type = fields.Selection([
        ('earn', 'Earn Points'),
        ('redeem', 'Redeem Points'),
        ('expire', 'Points Expiration')
    ], required=True, default='redeem')
    description = fields.Text()
    discount_amount = fields.Float(string="Discount Amount")