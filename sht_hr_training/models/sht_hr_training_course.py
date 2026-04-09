# -*- coding: utf-8 -*-

from odoo import fields, models


class ShtHrTrainingCourse(models.Model):
    _name = 'sht.hr.training.course'
    _description = 'Training Course'

    name = fields.Char(required=True)
    code = fields.Char()
    category = fields.Selection(
        [
            ('internal', 'Internal'),
            ('external', 'External'),
            ('online', 'Online'),
        ],
        default='internal',
    )
    description = fields.Html()
    duration_hours = fields.Float(string='Duration (hours)')
    provider = fields.Char(string='Training Provider')
    is_active = fields.Boolean(default=True)
