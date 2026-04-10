# -*- coding: utf-8 -*-

from odoo import _, api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    training_ids = fields.One2many(
        'sht.hr.training',
        'employee_id',
        string='Training Records',
    )
    training_count = fields.Integer(compute='_compute_training_count')

    @api.depends('training_ids')
    def _compute_training_count(self):
        for employee in self:
            employee.training_count = len(employee.training_ids)

    def action_open_sht_hr_training(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Training Records'),
            'res_model': 'sht.hr.training',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }
