# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    checklist_ids = fields.One2many(
        'sht.hr.checklist',
        'employee_id',
        string='Checklists',
    )
    checklist_count = fields.Integer(compute='_compute_checklist_count')

    @api.depends('checklist_ids')
    def _compute_checklist_count(self):
        for employee in self:
            employee.checklist_count = len(employee.checklist_ids)

    def action_open_checklists(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Checklists',
            'res_model': 'sht.hr.checklist',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }
