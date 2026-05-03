# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ShtHrHeadcountPlan(models.Model):
    _name = 'sht.hr.headcount.plan'
    _description = 'Kế hoạch định biên'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_from desc'

    name = fields.Char(string='Tên kế hoạch', required=True, tracking=True)
    department_id = fields.Many2one(
        'hr.department', string='Phòng ban', required=True, ondelete='restrict', tracking=True,
    )
    job_id = fields.Many2one(
        'hr.job', string='Vị trí công việc', required=True, ondelete='restrict', tracking=True,
    )
    planned_count = fields.Integer(
        string='Số lượng định biên', required=True, tracking=True,
    )
    current_count = fields.Integer(string='Nhân viên hiện tại', compute='_compute_current_count')
    applicant_count = fields.Integer(string='Ứng viên đang tuyển', compute='_compute_applicant_count')
    remaining = fields.Integer(string='Còn thiếu', compute='_compute_remaining')
    is_over_budget = fields.Boolean(
        string='Vượt định biên', compute='_compute_remaining', store=True,
    )
    date_from = fields.Date(string='Từ ngày', required=True)
    date_to = fields.Date(string='Đến ngày', required=True)
    state = fields.Selection(
        [('draft', 'Nháp'), ('approved', 'Đã duyệt'), ('closed', 'Đã đóng')],
        string='Trạng thái', default='draft', required=True, copy=False, tracking=True,
    )
    note = fields.Text(string='Ghi chú')
    company_id = fields.Many2one(
        'res.company', string='Công ty', required=True,
        default=lambda self: self.env.company,
    )

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        today = fields.Date.today()
        for plan in self:
            if plan.date_from and plan.date_to and plan.date_to < plan.date_from:
                raise ValidationError(
                    _('Ngày kết thúc phải sau ngày bắt đầu.')
                )
            if plan.date_from and plan.date_from < today:
                raise ValidationError(
                    _('Ngày bắt đầu kế hoạch không thể trong quá khứ.')
                )

    @api.constrains('planned_count')
    def _check_planned_count(self):
        for plan in self:
            if plan.planned_count <= 0:
                raise ValidationError(
                    _('Số lượng định biên phải lớn hơn 0.')
                )

    @api.depends('department_id', 'job_id', 'company_id')
    def _compute_current_count(self):
        Employee = self.env['hr.employee']
        for plan in self:
            if not plan.department_id or not plan.job_id:
                plan.current_count = 0
                continue
            plan.current_count = Employee.search_count([
                ('active', '=', True),
                ('department_id', '=', plan.department_id.id),
                ('job_id', '=', plan.job_id.id),
                ('company_id', '=', plan.company_id.id),
            ])

    @api.depends('department_id', 'job_id', 'company_id')
    def _compute_applicant_count(self):
        Applicant = self.env['hr.applicant']
        for plan in self:
            if not plan.department_id or not plan.job_id:
                plan.applicant_count = 0
                continue
            plan.applicant_count = Applicant.search_count([
                ('department_id', '=', plan.department_id.id),
                ('job_id', '=', plan.job_id.id),
                ('company_id', '=', plan.company_id.id),
            ])

    @api.depends('planned_count', 'current_count')
    def _compute_remaining(self):
        for plan in self:
            plan.remaining = plan.planned_count - plan.current_count
            plan.is_over_budget = plan.current_count > plan.planned_count

    def action_approve(self):
        for plan in self:
            if plan.state != 'draft':
                raise UserError(_('Chỉ duyệt kế hoạch ở trạng thái Nháp.'))
            if plan.date_to < fields.Date.today():
                raise UserError(_('Không thể duyệt kế hoạch đã hết hạn.'))
        self.write({'state': 'approved'})

    def action_close(self):
        self.write({'state': 'closed'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    @api.model
    def _cron_close_expired_plans(self):
        """Auto-close plans past date_to."""
        expired = self.search([
            ('state', '=', 'approved'),
            ('date_to', '<', fields.Date.today()),
        ])
        if expired:
            expired.write({'state': 'closed'})
