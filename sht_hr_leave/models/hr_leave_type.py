# -*- coding: utf-8 -*-

from odoo import fields, models


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    sht_is_vietnam_legal = fields.Boolean(
        string='Vietnam Legal Leave',
        help='This leave type is mandated by Vietnamese labor law',
    )
    sht_seniority_bonus = fields.Boolean(
        string='Seniority Bonus Applies',
        help='Add 1 extra day per 5 years of seniority',
    )
    sht_max_days = fields.Float(
        string='Base Annual Days',
        help='Base number of days per year before seniority bonus',
    )
