from odoo import models,fields,api
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


    def write(self, vals):
        res = super(ProductProduct, self).write(vals)
        if 'free_qty' not in vals:
            self._compute_free_qty()
        return res

    @api.depends('qty_available')
    def _compute_free_qty(self):
        for product in self:
            product.free_qty = product.qty_available