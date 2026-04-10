from odoo import api, fields, models


class ShtHrAppraisalCriteria(models.Model):
    _name = 'sht.hr.appraisal.criteria'
    _description = 'Tiêu chí đánh giá'
    _order = 'category, sequence, name'

    name = fields.Char(string='Tên tiêu chí', required=True)
    code = fields.Char(string='Mã')
    sequence = fields.Integer(string='Thứ tự', default=10)
    category = fields.Selection([
        ('attitude', 'Thái độ (A)'),
        ('skill', 'Kỹ năng (S)'),
        ('knowledge', 'Kiến thức (K)'),
    ], string='Nhóm ASK', required=True)
    description = fields.Text(string='Mô tả')
    weight = fields.Float(string='Trọng số (%)', default=10.0)
    active = fields.Boolean(string='Hoạt động', default=True)
    company_id = fields.Many2one(
        'res.company', string='Công ty',
        default=lambda self: self.env.company,
    )
