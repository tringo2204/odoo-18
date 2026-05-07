from odoo import fields, models, _
from odoo.exceptions import UserError


class HrVnAssetDisposalReject(models.TransientModel):
    _name = 'hr.vn.asset.disposal.reject'
    _description = 'Wizard từ chối biên bản thanh lý'

    disposal_id = fields.Many2one('hr.vn.asset.disposal', required=True)
    rejection_reason = fields.Text(string='Lý do từ chối', required=True)

    def action_confirm_reject(self):
        for wizard in self:
            if wizard.disposal_id.state != 'submitted':
                raise UserError(_('Chỉ có thể từ chối biên bản đang ở trạng thái Chờ duyệt.'))
            wizard.disposal_id.write({
                'state': 'rejected',
                'rejection_reason': wizard.rejection_reason,
            })
