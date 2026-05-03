from odoo import fields, models, _
from odoo.exceptions import UserError


class HrRequestActionWizard(models.TransientModel):
    _name = 'hr.request.action.wizard'
    _description = 'Ghi chú phê duyệt / từ chối đơn từ'

    request_id = fields.Many2one('hr.request', required=True, ondelete='cascade')
    action_type = fields.Selection(
        [('approve', 'Phê duyệt'), ('refuse', 'Từ chối')],
        required=True,
    )
    note = fields.Text(string='Nhận xét của người duyệt')

    def action_confirm(self):
        self.ensure_one()
        request = self.request_id
        pending = request.approval_ids.filtered(
            lambda a: a.status == 'pending' and a.approver_id == self.env.user
        )
        if not pending:
            raise UserError(_('Bạn không có quyền thực hiện thao tác này.'))

        if self.action_type == 'approve':
            pending[0].write({
                'status': 'approved',
                'approved_date': fields.Datetime.now(),
                'note': self.note or '',
            })
            all_done = all(
                a.status == 'approved'
                for a in request.approval_ids
                if a.status != 'refused'
            )
            if all_done:
                request.write({'state': 'approved'})
                request._execute_side_effects()
        else:
            pending[0].write({
                'status': 'refused',
                'approved_date': fields.Datetime.now(),
                'note': self.note or '',
            })
            request.write({'state': 'refused'})

        return {'type': 'ir.actions.act_window_close'}
