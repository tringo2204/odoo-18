# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ShtHrChecklistLine(models.Model):
    _name = 'sht.hr.checklist.line'
    _description = 'Employee Checklist Line'
    _order = 'sequence, id'

    name = fields.Char(required=True)
    checklist_id = fields.Many2one(
        'sht.hr.checklist',
        required=True,
        ondelete='cascade',
    )
    sequence = fields.Integer(default=10)
    responsible_role = fields.Selection(
        [
            ('hr', 'HR'),
            ('manager', 'Manager'),
            ('it', 'IT'),
            ('employee', 'Employee'),
        ],
        default='hr',
        required=True,
    )
    is_done = fields.Boolean(default=False)
    done_by = fields.Many2one('res.users', string='Done By', readonly=True)
    done_date = fields.Date(readonly=True)
    note = fields.Text()

    def write(self, vals):
        vals = dict(vals)
        if 'is_done' in vals:
            if vals['is_done']:
                if 'done_by' not in vals:
                    vals['done_by'] = self.env.user.id
                if 'done_date' not in vals:
                    vals['done_date'] = fields.Date.today()
            else:
                vals['done_by'] = False
                vals['done_date'] = False
        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('is_done'):
                vals.setdefault('done_by', self.env.user.id)
                vals.setdefault('done_date', fields.Date.today())
        return super().create(vals_list)
