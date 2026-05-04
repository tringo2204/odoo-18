# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    rd_ids = fields.One2many(
        'sht.hr.rd',
        'employee_id',
        string='Reward & Discipline',
        groups='hr.group_hr_user',
    )
    rd_count = fields.Integer(compute='_compute_rd_counts', groups='hr.group_hr_user')
    reward_count = fields.Integer(compute='_compute_rd_counts', groups='hr.group_hr_user')
    discipline_count = fields.Integer(compute='_compute_rd_counts', groups='hr.group_hr_user')

    @api.depends('rd_ids', 'rd_ids.category')
    def _compute_rd_counts(self):
        for employee in self:
            records = employee.rd_ids
            employee.rd_count = len(records)
            employee.reward_count = len(records.filtered(lambda r: r.category == 'reward'))
            employee.discipline_count = len(records.filtered(lambda r: r.category == 'discipline'))

    def action_open_rd_records(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Khen thưởng & Kỷ luật',
            'res_model': 'sht.hr.rd',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }

    def action_open_reward_records(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Khen thưởng',
            'res_model': 'sht.hr.rd',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id), ('category', '=', 'reward')],
            'context': {'default_employee_id': self.id, 'default_category': 'reward'},
        }

    def action_open_discipline_records(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Kỷ luật',
            'res_model': 'sht.hr.rd',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id), ('category', '=', 'discipline')],
            'context': {'default_employee_id': self.id, 'default_category': 'discipline'},
        }
