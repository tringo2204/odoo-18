# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    campaign_id = fields.Many2one(
        'sht.hr.recruitment.campaign', string='Chiến dịch tuyển dụng',
    )
    evaluation_ids = fields.One2many(
        'sht.hr.applicant.evaluation', 'applicant_id',
        string='Đánh giá ứng viên',
    )
    evaluation_score = fields.Float(
        string='Điểm đánh giá', compute='_compute_evaluation_score',
    )
    source_channel = fields.Selection([
        ('website', 'Website'),
        ('referral', 'Giới thiệu'),
        ('agency', 'Đơn vị TD'),
        ('social', 'Mạng XH'),
        ('other', 'Khác'),
    ], string='Nguồn ứng viên')

    headcount_plan_id = fields.Many2one(
        'sht.hr.headcount.plan',
        string='Headcount Plan',
        domain="['&', '|', ('company_id', '=', False), ('company_id', '=', company_id), ('state', '!=', 'closed')]",
    )
    is_over_budget = fields.Boolean(
        related='headcount_plan_id.is_over_budget',
        string='Over Budget',
    )

    @api.model_create_multi
    def create(self, vals_list):
        applicants = super().create(vals_list)
        for applicant in applicants:
            if applicant.headcount_plan_id and applicant.is_over_budget:
                _logger.warning(
                    'Applicant %s created with headcount plan over budget.',
                    applicant.display_name,
                )
                applicant.activity_schedule(
                    act_type_xmlid='mail.mail_activity_data_warning',
                    summary=_('Headcount over budget'),
                    note=_(
                        'The selected headcount plan is over budget (current headcount exceeds planned).'
                    ),
                    user_id=applicant.user_id.id or self.env.user.id,
                )
        return applicants

    @api.depends('evaluation_ids.overall_score')
    def _compute_evaluation_score(self):
        for rec in self:
            evals = rec.evaluation_ids
            if evals:
                rec.evaluation_score = sum(
                    evals.mapped('overall_score')
                ) / len(evals)
            else:
                rec.evaluation_score = 0

    def create_employee_from_applicant(self):
        """Override to also create a draft contract pre-filled from recruitment data."""
        self.ensure_one()
        result = super().create_employee_from_applicant()
        employee = self.env['hr.employee'].browse(result.get('res_id'))
        if not employee.exists():
            return result
        # Find VN salary structure type first, fallback to any
        structure_type = (
            self.env.ref('hr_payroll_vietnam.structure_type_vn_employee', raise_if_not_found=False)
            or self.env['hr.payroll.structure.type'].search([], limit=1)
        )
        # Find default contract type
        contract_type = self.env['hr.contract.type'].search([], limit=1)
        contract_vals = {
            'name': _('Hợp đồng - %s') % employee.name,
            'employee_id': employee.id,
            'job_id': self.job_id.id if self.job_id else False,
            'department_id': self.department_id.id if self.department_id else False,
            'company_id': self.company_id.id or self.env.company.id,
            'state': 'draft',
            'wage': self.salary_proposed or 0.0,
        }
        if structure_type:
            contract_vals['structure_type_id'] = structure_type.id
        if contract_type:
            contract_vals['contract_type_id'] = contract_type.id
        self.env['hr.contract'].sudo().create(contract_vals)
        return result
