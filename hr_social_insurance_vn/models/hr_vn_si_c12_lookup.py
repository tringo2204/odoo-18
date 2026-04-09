from odoo import api, fields, models


class HrVnSiC12Lookup(models.Model):
    _name = 'hr.vn.si.c12.lookup'
    _description = 'Tra cứu C12 (Biến động BHXH tháng)'
    _order = 'year desc, month desc, employee_id'

    month = fields.Selection([
        ('1', 'Tháng 1'), ('2', 'Tháng 2'), ('3', 'Tháng 3'),
        ('4', 'Tháng 4'), ('5', 'Tháng 5'), ('6', 'Tháng 6'),
        ('7', 'Tháng 7'), ('8', 'Tháng 8'), ('9', 'Tháng 9'),
        ('10', 'Tháng 10'), ('11', 'Tháng 11'), ('12', 'Tháng 12'),
    ], string='Tháng', required=True)
    year = fields.Integer(string='Năm', required=True)
    employee_id = fields.Many2one(
        'hr.employee', string='Nhân viên', required=True,
    )
    bhxh_number = fields.Char(
        string='Số sổ BHXH',
        related='employee_id.social_insurance_id', store=True,
    )
    bhxh_status = fields.Char(string='Tình trạng tham gia')
    bhxh_amount = fields.Float(string='BHXH')
    bhyt_amount = fields.Float(string='BHYT')
    bhtn_amount = fields.Float(string='BHTN')
    total_amount = fields.Float(
        string='Tổng cộng', compute='_compute_total', store=True,
    )
    import_date = fields.Datetime(
        string='Ngày import',
        default=fields.Datetime.now, readonly=True,
    )
    company_id = fields.Many2one(
        'res.company', string='Công ty',
        default=lambda self: self.env.company,
    )

    @api.depends('bhxh_amount', 'bhyt_amount', 'bhtn_amount')
    def _compute_total(self):
        for rec in self:
            rec.total_amount = (
                rec.bhxh_amount + rec.bhyt_amount + rec.bhtn_amount
            )
