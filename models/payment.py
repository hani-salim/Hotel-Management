from odoo import models, fields, api
from odoo.exceptions import UserError


class AccountPaymentInherit(models.Model):
    _inherit = 'account.payment'

    # الحقول الجديدة للفندق
    guest_id = fields.Many2one('hotel.guest', string='الضيف', related='invoice_ids.guest_id', store=True)
    invoice_ids = fields.Many2many(
        'account.move',
        string='Payments',
        relation='account_payment_invoice_rel',
        column1='payment_id',
        column2='invoice_id',
        readonly=True,
        states={'draft': [('readonly', False)]}
    )

