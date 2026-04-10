from odoo import fields, models


class HrKpiCriteria(models.Model):
    _name = 'hr.kpi.criteria'
    _description = 'Tiêu chí KPI'
    _order = 'category, sequence'

    name = fields.Char(string='Tên tiêu chí', required=True)
    code = fields.Char(string='Mã')
    sequence = fields.Integer(default=10)
    category = fields.Selection([
        ('performance', 'Hiệu suất'),
        ('behavior', 'Hành vi'),
        ('result', 'Kết quả'),
    ], string='Nhóm', required=True)
    unit = fields.Selection([
        ('percent', '%'),
        ('number', 'Số'),
        ('currency', 'VND'),
        ('rating', 'Điểm (1-5)'),
    ], string='Đơn vị', default='rating')
    target_value = fields.Float(string='Mục tiêu', default=100)
    weight = fields.Float(string='Trọng số (%)', default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', string='Công ty',
        default=lambda self: self.env.company,
    )
    description = fields.Text(string='Mô tả')
