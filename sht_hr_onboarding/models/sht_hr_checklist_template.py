# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ShtHrChecklistTemplate(models.Model):
    _name = 'sht.hr.checklist.template'
    _description = 'HR Checklist Template'
    _order = 'name'

    name = fields.Char(required=True)
    checklist_type = fields.Selection(
        [('onboarding', 'Onboarding'), ('offboarding', 'Offboarding')],
        required=True,
    )
    department_id = fields.Many2one('hr.department', string='Phòng ban')
    job_id = fields.Many2one('hr.job', string='Vị trí công việc')
    line_ids = fields.One2many(
        'sht.hr.checklist.template.line', 'template_id', string='Lines',
    )
    is_active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', string='Công ty',
        default=lambda self: self.env.company,
    )

    @api.model
    def find_matching_template(self, checklist_type, department_id=False, job_id=False, company_id=False):
        domain = [('checklist_type', '=', checklist_type), ('is_active', '=', True)]
        if company_id:
            domain += ['|', ('company_id', '=', company_id), ('company_id', '=', False)]
        templates = self.search(domain)
        if not templates:
            return self.browse()
        if department_id and job_id:
            exact = templates.filtered(
                lambda t: t.department_id.id == department_id and t.job_id.id == job_id
            )
            if exact:
                return exact[0]
        if department_id:
            dept_only = templates.filtered(
                lambda t: t.department_id.id == department_id and not t.job_id
            )
            if dept_only:
                return dept_only[0]
        general = templates.filtered(lambda t: not t.department_id and not t.job_id)
        return general[0] if general else self.browse()
