# -*- coding: utf-8 -*-
from odoo import fields, models


class ShtHrRdType(models.Model):
    _name = 'sht.hr.rd.type'
    _description = 'Loại Quyết định Khen thưởng/Kỷ luật'

    name = fields.Char(required=True)
    code = fields.Char()
    category = fields.Selection(
        [('reward', 'Khen thưởng'), ('discipline', 'Kỷ luật')],
        required=True,
    )
    description = fields.Text()
