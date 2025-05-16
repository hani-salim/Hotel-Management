from odoo import models, fields, api
from odoo.exceptions import UserError


class AccountPaymentInherit(models.Model):
    _inherit = 'account.payment'

    # الحقول الجديدة للفندق
    guest_id = fields.Many2one('hotel.guest', string='الضيف', related='invoice_ids.guest_id', store=True)
    invoice_ids = fields.Many2many(
        'account.move',
        string='الفواتير',
        relation='account_payment_invoice_rel',
        column1='payment_id',
        column2='invoice_id',
        readonly=True,
        states={'draft': [('readonly', False)]}
    )

    # def action_post(self):
    #     """تجاوز إجراء التأكيد لإضافة منطق الفندق"""
    #     res = super().action_post()
    #
    #     for payment in self:
    #         if payment.invoice_ids and payment.invoice_ids[0].is_hotel_invoice:
    #             invoice = payment.invoice_ids[0]
    #             if invoice.payment_state == 'paid':
    #                 # يمكن إضافة أي إجراءات إضافية عند اكتمال الدفع
    #                 invoice.room_id.message_post(
    #                     body=f"تم اكتمال الدفع للفاتورة {invoice.name}"
    #                 )
    #     return res
    #
    # @api.model
    # def create_hotel_payment(self, invoice, amount, payment_method='cash'):
    #     """إنشاء دفعة فندقية تلقائية"""
    #     payment = self.create({
    #         'payment_type': 'inbound',
    #         'partner_id': invoice.partner_id.id,
    #         'amount': amount,
    #         'date': fields.Date.today(),
    #         'journal_id': self.env['account.journal'].search([('type', '=', 'cash')], limit=1).id,
    #         'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id,
    #         'invoice_ids': [(6, 0, invoice.ids)],
    #         'payment_method': payment_method
    #     })
    #     return payment