from odoo import models,fields

class HotelOccupancyWizard(models.TransientModel):
    _name = 'hotel.occupancy.wizard'
    _description = 'Occupancy Report Wizard'

    date_from = fields.Date(string='From Date', required=True, default=fields.Date.context_today)
    date_to = fields.Date(string='To Date', required=True, default=fields.Date.context_today)

    def action_generate_report(self):
        data = {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'doc_ids': [],
            'doc_model': 'hotel.room'
        }
        return self.env.ref('hotel.action_report_occupancy').report_action([], data=data)