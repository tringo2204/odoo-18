from odoo import fields, models


class HrVnPitBracket(models.Model):
    _name = 'hr.vn.pit.bracket'
    _description = 'Biểu thuế TNCN lũy tiến'
    _order = 'year desc, bracket_no'

    year = fields.Integer(string='Năm', required=True)
    bracket_no = fields.Integer(string='Bậc', required=True)
    income_from = fields.Float(string='Thu nhập từ')
    income_to = fields.Float(string='Thu nhập đến', help='0 = không giới hạn (bậc cuối)')
    tax_rate = fields.Float(string='Thuế suất (%)')
    company_id = fields.Many2one(
        'res.company', string='Công ty', default=lambda self: self.env.company,
    )
