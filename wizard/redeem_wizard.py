from odoo import models, fields, api
from odoo.exceptions import UserError


class RedeemWizard(models.TransientModel):
    _name = 'loyalty.redeem.wizard'
    _description = 'Loyalty Redeem Wizard'

    reward_id = fields.Many2one('loyalty.reward', required=True)
    guest_id = fields.Many2one('hotel.guest', required=True)
    discount_amount = fields.Float(string="Discount Amount", compute='_compute_discount_amount')

    @api.depends('reward_id')
    def _compute_discount_amount(self):
        for wizard in self:
            if wizard.reward_id.reward_type == 'discount':
                wizard.discount_amount = wizard.reward_id.discount_percent
            else:
                wizard.discount_amount = 0.0

    def action_confirm(self):
        self.ensure_one()

        if self.guest_id.loyalty_points < self.reward_id.points_cost:
            raise UserError("Not enough loyalty points for this reward!")

        # خصم النقاط
        self.guest_id.write({
            'loyalty_points': self.guest_id.loyalty_points - self.reward_id.points_cost
        })

        # تسجيل الحركة
        self.env['loyalty.transaction'].create({
            'guest_id': self.guest_id.id,
            'points': -self.reward_id.points_cost,
            'reward_id': self.reward_id.id
        })

        # تطبيق الخصم فقط إذا كان نوع المكافأة هو خصم
        if self.reward_id.reward_type == 'discount':
            return self._apply_discount()

        # إذا كانت المكافأة ليست خصمًا، نعيد رسالة بسيطة
        return {'type': 'ir.actions.act_window_close'}

    def _apply_discount(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Apply Discount',
            'res_model': 'account.move',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_guest_id': self.guest_id.id,
                'default_loyalty_discount': self.discount_amount,
                'default_loyalty_reward_id': self.reward_id.id
            },
            'result': {
                'discount': self.discount_amount,
                'reward_id': self.reward_id.id
            }
        }