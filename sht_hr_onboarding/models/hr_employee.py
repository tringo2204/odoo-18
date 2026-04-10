# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    checklist_ids = fields.One2many('sht.hr.checklist', 'employee_id', string='Checklists')
    checklist_count = fields.Integer(compute='_compute_checklist_count')
    onboarding_progress = fields.Float(compute='_compute_onboarding_progress', string='Tiến độ Onboarding')
    offboarding_ids = fields.One2many('sht.hr.offboarding', 'employee_id', string='Quy trình thôi việc')
    offboarding_count = fields.Integer(compute='_compute_offboarding_count')

    @api.depends('checklist_ids')
    def _compute_checklist_count(self):
        for emp in self:
            emp.checklist_count = len(emp.checklist_ids)

    @api.depends('checklist_ids.progress', 'checklist_ids.checklist_type', 'checklist_ids.state')
    def _compute_onboarding_progress(self):
        for emp in self:
            onboarding = emp.checklist_ids.filtered(
                lambda c: c.checklist_type == 'onboarding' and c.state == 'in_progress'
            )
            emp.onboarding_progress = onboarding[:1].progress if onboarding else 0.0

    @api.depends('offboarding_ids')
    def _compute_offboarding_count(self):
        for emp in self:
            emp.offboarding_count = len(emp.offboarding_ids)

    def action_open_checklists(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': 'Checklists',
            'res_model': 'sht.hr.checklist', 'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }

    def action_open_offboardings(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': 'Quy trình thôi việc',
            'res_model': 'sht.hr.offboarding', 'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }

    def action_create_onboarding(self):
        self.ensure_one()
        existing = self.checklist_ids.filtered(
            lambda c: c.checklist_type == 'onboarding' and c.state == 'in_progress'
        )
        if existing:
            return {'type': 'ir.actions.act_window', 'name': 'Onboarding',
                    'res_model': 'sht.hr.checklist', 'view_mode': 'form', 'res_id': existing[0].id}
        template = self.env['sht.hr.checklist.template'].find_matching_template(
            'onboarding', department_id=self.department_id.id,
            job_id=self.job_id.id, company_id=self.company_id.id,
        )
        checklist = self.env['sht.hr.checklist'].create({
            'employee_id': self.id, 'checklist_type': 'onboarding',
            'template_id': template.id if template else False,
            'company_id': self.company_id.id,
        })
        if template:
            checklist.action_generate_lines()
        return {'type': 'ir.actions.act_window', 'name': 'Onboarding',
                'res_model': 'sht.hr.checklist', 'view_mode': 'form', 'res_id': checklist.id}

    def action_create_offboarding(self):
        self.ensure_one()
        existing = self.env['sht.hr.offboarding'].search([
            ('employee_id', '=', self.id), ('state', 'not in', ['completed', 'cancelled']),
        ], limit=1)
        if existing:
            return {'type': 'ir.actions.act_window', 'res_model': 'sht.hr.offboarding',
                    'view_mode': 'form', 'res_id': existing.id}
        offboarding = self.env['sht.hr.offboarding'].create({
            'employee_id': self.id, 'company_id': self.company_id.id,
        })
        return {'type': 'ir.actions.act_window', 'name': 'Quy trình thôi việc',
                'res_model': 'sht.hr.offboarding', 'view_mode': 'form', 'res_id': offboarding.id}
