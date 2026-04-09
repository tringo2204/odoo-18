from odoo import api, fields, models


class HrVnRegionalWage(models.Model):
    _name = 'hr.vn.regional.wage'
    _description = 'Lương tối thiểu vùng'
    _order = 'region'

    config_id = fields.Many2one(
        'hr.vn.insurance.config', string='Cấu hình BHXH',
        required=True, ondelete='cascade',
    )
    region = fields.Selection([
        ('1', 'Vùng I'),
        ('2', 'Vùng II'),
        ('3', 'Vùng III'),
        ('4', 'Vùng IV'),
    ], string='Vùng', required=True)
    wage_amount = fields.Float(string='Mức lương tối thiểu vùng')
    bhtn_cap = fields.Float(
        string='Mức trần BHTN', compute='_compute_bhtn_cap', store=True,
    )

    @api.depends('wage_amount')
    def _compute_bhtn_cap(self):
        for rec in self:
            rec.bhtn_cap = rec.wage_amount * 20
