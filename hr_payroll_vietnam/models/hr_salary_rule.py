from odoo import fields, models


class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    # #Fix Row 201: thêm field 'Ghi chú' tách biệt với 'Mô tả' (note Enterprise)
    user_note = fields.Html(string='Ghi chú', translate=True)
