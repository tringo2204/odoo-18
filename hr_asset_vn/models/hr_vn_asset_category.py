from odoo import fields, models


class HrVnAssetCategory(models.Model):
    _name = 'hr.vn.asset.category'
    _description = 'Danh mục tài sản'
    _order = 'name'

    name = fields.Char(string='Tên danh mục', required=True)
    parent_id = fields.Many2one('hr.vn.asset.category', string='Danh mục cha')
    depreciation_years = fields.Integer(string='Số năm khấu hao', default=3)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', string='Công ty', default=lambda self: self.env.company,
    )
