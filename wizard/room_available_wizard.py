
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta


class RoomAvailabilityWizard(models.TransientModel):
    _name = 'hotel.room.availability.wizard'
    _description = 'Check Room Availability Wizard'

    check_in = fields.Datetime(string='Check-in Date', required=True, default=fields.Datetime.now)
    check_out = fields.Datetime(string='Check-out Date', required=True)

    @api.constrains('check_in', 'check_out')
    def _check_dates(self):
        for record in self:
            if record.check_out <= record.check_in:
                raise UserError(_("Check-out date must be after check-in date"))

    def action_check_availability(self):
        self.ensure_one()
        available_rooms = self.env['hotel.booking'].get_available_rooms(
            self.check_in,
            self.check_out
        )
        print(available_rooms)

        return {
            'name': _('Available Rooms (%s - %s)') % (
                self.check_in.strftime('%Y-%m-%d'),
                self.check_out.strftime('%Y-%m-%d')
            ),
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.room',
            'view_mode': 'kanban,tree,form',
            'domain': [('id', 'in', available_rooms.ids)],
            'target': 'current',
            'context': {
                'default_check_in_date': self.check_in,
                'default_check_out_date': self.check_out,
                'available_room_ids': available_rooms.ids
            }
        }


