# -*- coding: utf-8 -*-
from odoo import fields, models


class ShtHrRdType(models.Model):
    _name = 'sht.hr.rd.type'
    _description = 'Reward & Discipline Type'

    name = fields.Char(required=True)
    code = fields.Char()
    category = fields.Selection(
        [('reward', 'Reward'), ('discipline', 'Discipline')],
        required=True,
    )
    description = fields.Text()
