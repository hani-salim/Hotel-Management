from odoo import http
from odoo.http import request

class HotelController(http.Controller):

    @http.route('/hotel/current_guests', methods=['GET'], type='http', auth='none', csrf=False)
    def get_current_guests(self):
        rooms = request.env['hotel.room'].sudo().search([
            ('current_guest_id', '!=', False)
        ])

        guests = []
        for room in rooms:
            guest = room.current_guest_id
            if guest:
                guests.append({
                    'id': guest.id,
                    'partner_id': guest.partner_id,
                })
        return guests
