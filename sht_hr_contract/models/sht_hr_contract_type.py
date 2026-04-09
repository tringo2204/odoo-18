# -*- coding: utf-8 -*-
from odoo import fields, models


class ShtHrContractType(models.Model):
    _name = 'sht.hr.contract.type'
    _description = 'Vietnam Contract Type'

    name = fields.Char(required=True, translate=True)
    code = fields.Char()
    max_duration_months = fields.Integer(string='Max duration (months)')
    description = fields.Text(translate=True)
