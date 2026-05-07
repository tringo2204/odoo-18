# -*- coding: utf-8 -*-
from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    health_record_ids = fields.One2many(
        'sht.hr.health.record', 'employee_id',
        string='Hồ sơ sức khoẻ',
    )
    health_record_count = fields.Integer(
        string='Số lần khám', compute='_compute_health_record_count',
    )

    def _compute_health_record_count(self):
        data = self.env['sht.hr.health.record'].read_group(
            [('employee_id', 'in', self.ids)],
            ['employee_id'],
            ['employee_id'],
        )
        mapped = {d['employee_id'][0]: d['employee_id_count'] for d in data}
        for emp in self:
            emp.health_record_count = mapped.get(emp.id, 0)

    def action_open_health_records(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Hồ sơ sức khoẻ',
            'res_model': 'sht.hr.health.record',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }
