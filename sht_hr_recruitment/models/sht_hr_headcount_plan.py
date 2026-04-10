# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ShtHrHeadcountPlan(models.Model):
    _name = 'sht.hr.headcount.plan'
    _description = 'Headcount Plan'

    name = fields.Char(required=True)
    department_id = fields.Many2one('hr.department', required=True, ondelete='restrict')
    job_id = fields.Many2one('hr.job', required=True, ondelete='restrict')
    planned_count = fields.Integer(string='Planned Headcount', required=True)
    current_count = fields.Integer(compute='_compute_headcount_metrics')
    remaining = fields.Integer(compute='_compute_headcount_metrics')
    is_over_budget = fields.Boolean(compute='_compute_headcount_metrics', store=True)
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    state = fields.Selection(
        [('draft', 'Draft'), ('approved', 'Approved'), ('closed', 'Closed')],
        default='draft',
        required=True,
        copy=False,
    )
    note = fields.Text()
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
    )

    @api.depends('department_id', 'job_id', 'company_id', 'planned_count')
    def _compute_headcount_metrics(self):
        Employee = self.env['hr.employee']
        for plan in self:
            if not plan.department_id or not plan.job_id:
                plan.current_count = 0
                plan.remaining = plan.planned_count
                plan.is_over_budget = plan.current_count > plan.planned_count
                continue
            cnt = Employee.search_count([
                ('active', '=', True),
                ('department_id', '=', plan.department_id.id),
                ('job_id', '=', plan.job_id.id),
                ('company_id', '=', plan.company_id.id),
            ])
            plan.current_count = cnt
            plan.remaining = plan.planned_count - cnt
            plan.is_over_budget = cnt > plan.planned_count

    def action_approve(self):
        self.write({'state': 'approved'})
        return True

    def action_close(self):
        self.write({'state': 'closed'})
        return True

    def action_reset_draft(self):
        self.write({'state': 'draft'})
        return True
