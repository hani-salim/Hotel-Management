from odoo import models, fields, api



class HotelService(models.Model):
    _name = 'hotel.service'
    _description = 'Hotel Service'

    name = fields.Char(string='Service Name', required=True)
    product_id = fields.Many2one('product.product', string='Related Product', required=True)
    price = fields.Float(string='Price', related='product_id.list_price')
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Active', default=True)