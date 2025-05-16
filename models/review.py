from odoo import models, fields, api


class HotelReview(models.Model):
    _name = 'hotel.review'
    _description = 'Guest Review'

    guest_id = fields.Many2one('hotel.guest', string='Guest', required=True)
    rating = fields.Integer(string='Rating (1-5)')
    comment = fields.Text(string='Comment')
    date = fields.Datetime(string='Date', default=fields.Datetime.now)