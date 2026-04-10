from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    approval_state = fields.Selection([
        ('draft', 'Nháp'), ('computed', 'Đã tính'), ('verified', 'Đã kiểm tra'),
        ('approved', 'Đã duyệt'), ('paid', 'Đã trả lương'),
    ], string='Trạng thái duyệt', default='draft', tracking=True)
    approved_by = fields.Many2one('res.users', string='Người duyệt', readonly=True)
    approved_date = fields.Datetime(string='Ngày duyệt', readonly=True)
    total_gross = fields.Float(string='Tổng GROSS', compute='_compute_totals', store=True)
    total_net = fields.Float(string='Tổng NET', compute='_compute_totals', store=True)
    total_insurance = fields.Float(string='Tổng BHXH (NV)', compute='_compute_totals', store=True)
    total_pit = fields.Float(string='Tổng thuế TNCN', compute='_compute_totals', store=True)
    employee_count = fields.Integer(string='Số nhân viên', compute='_compute_totals', store=True)

    @api.depends('slip_ids', 'slip_ids.state', 'slip_ids.line_ids')
    def _compute_totals(self):
        for run in self:
            slips = run.slip_ids
            run.employee_count = len(slips)
            run.total_gross = sum(self._get_rule_total(s, 'GROSS') for s in slips)
            run.total_net = sum(self._get_rule_total(s, 'NET') for s in slips)
            run.total_insurance = sum(
                abs(self._get_rule_total(s, 'BHXH_EE'))
                + abs(self._get_rule_total(s, 'BHYT_EE'))
                + abs(self._get_rule_total(s, 'BHTN_EE'))
                for s in slips)
            run.total_pit = sum(abs(self._get_rule_total(s, 'PIT')) for s in slips)

    @staticmethod
    def _get_rule_total(payslip, code):
        line = payslip.line_ids.filtered(lambda l: l.code == code)
        return line[0].total if line else 0

    def action_compute(self):
        # P2.3: Lifecycle gate — warn about incomplete onboarding
        if 'sht.hr.checklist' in self.env:
            for run in self:
                for slip in run.slip_ids:
                    emp = slip.employee_id
                    onboarding = self.env['sht.hr.checklist'].search([
                        ('employee_id', '=', emp.id),
                        ('checklist_type', '=', 'onboarding'),
                        ('state', '=', 'in_progress'),
                    ], limit=1)
                    if onboarding and onboarding.progress < 100:
                        slip.message_post(
                            body=_('Cảnh báo: NV %s chưa hoàn thành Onboarding (%.0f%%).') % (
                                emp.name, onboarding.progress),
                            message_type='notification',
                        )
        for run in self:
            run.slip_ids.compute_sheet()
        self.write({'approval_state': 'computed'})

    def action_verify(self):
        for run in self:
            if run.approval_state != 'computed':
                raise UserError(_('Phải tính lương trước khi kiểm tra.'))
        self.write({'approval_state': 'verified'})

    def action_approve(self):
        for run in self:
            if run.approval_state != 'verified':
                raise UserError(_('Phải kiểm tra trước khi duyệt.'))
        self.write({'approval_state': 'approved', 'approved_by': self.env.uid, 'approved_date': fields.Datetime.now()})

    def action_mark_paid(self):
        for run in self:
            if run.approval_state != 'approved':
                raise UserError(_('Phải duyệt trước khi đánh dấu đã trả.'))
        self.write({'approval_state': 'paid'})

    def action_reset_draft(self):
        self.write({'approval_state': 'draft'})

    def action_open_bank_export(self):
        self.ensure_one()
        if self.approval_state not in ('approved', 'paid'):
            raise UserError(_('Phải duyệt bảng lương trước khi xuất file.'))
        return {
            'type': 'ir.actions.act_window', 'name': _('Xuất file ngân hàng'),
            'res_model': 'hr.vn.bank.export', 'view_mode': 'form', 'target': 'new',
            'context': {'default_payslip_run_id': self.id},
        }
