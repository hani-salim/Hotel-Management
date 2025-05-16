from odoo import models, fields, api


class HotelServiceRequest(models.Model):
    _name = 'hotel.service.request'
    _description = 'Service Request'

    guest_id = fields.Many2one('hotel.guest', string='Guest', required=True)
    service_id = fields.Many2one('hotel.service', string='Service', required=True)
    request_date = fields.Datetime(string='Request Date', default=fields.Datetime.now)
    state = fields.Selection([
        ('requested', 'Requested'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='requested')
    notes = fields.Text(string='Notes')

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_complete(self):
        self.write({'state': 'completed'})
        # إضافة الخدمة إلى فاتورة الضيف
        invoice = self.env['hotel.invoice'].search([
            ('guest_id', '=', self.guest_id.id),
            ('state', '=', 'draft')
        ], limit=1)

        if not invoice:
            invoice = self.env['hotel.invoice'].create({
                'guest_id': self.guest_id.id,
                'room_id': self.guest_id.room_id.id
            })

        invoice.write({
            'invoice_line_ids': [(0, 0, {
                'product_id': self.service_id.product_id.id,
                'description': self.service_id.name,
                'quantity': 1,
                'price_unit': self.service_id.price
            })]
        })

    def action_cancel(self):
        self.write({'state': 'cancelled'})