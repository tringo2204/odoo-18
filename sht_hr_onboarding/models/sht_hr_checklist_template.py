# -*- coding: utf-8 -*-
from odoo import fields, models


class ShtHrChecklistTemplate(models.Model):
    _name = 'sht.hr.checklist.template'
    _description = 'HR Checklist Template'
    _order = 'name'

    name = fields.Char(required=True)
    checklist_type = fields.Selection(
        [('onboarding', 'Onboarding'), ('offboarding', 'Offboarding')],
        required=True,
    )
    line_ids = fields.One2many(
        'sht.hr.checklist.template.line',
        'template_id',
        string='Lines',
    )
    is_active = fields.Boolean(default=True)
