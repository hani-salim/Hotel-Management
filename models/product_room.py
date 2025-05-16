from odoo import models,fields
class ProductProduct(models.Model):
    _inherit = 'product.product'

    is_room = fields.Boolean(string='Is Room')
    room_category = fields.Selection([
        ('vip', 'VIP'),
        ('chalet', 'Chalet'),
        ('suite', 'Suite')
    ], string='Room Category')
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='company_id.currency_id',
        store=True
    )