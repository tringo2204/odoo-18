# -*- coding: utf-8 -*-
from odoo import fields, models


class ShtHrChecklistTemplateLine(models.Model):
    _name = 'sht.hr.checklist.template.line'
    _description = 'HR Checklist Template Line'
    _order = 'sequence, id'

    name = fields.Char(required=True)
    template_id = fields.Many2one(
        'sht.hr.checklist.template', required=True, ondelete='cascade',
    )
    sequence = fields.Integer(default=10)
    responsible_role = fields.Selection([
        ('hr', 'HR'), ('manager', 'Manager'), ('it', 'IT'), ('employee', 'Employee'),
    ], default='hr', required=True)
    description = fields.Text()
    default_deadline_days = fields.Integer(
        string='Hạn hoàn thành (ngày)', default=0,
    )
