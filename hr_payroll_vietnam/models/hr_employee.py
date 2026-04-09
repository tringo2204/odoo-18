from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # sht_hr_base already has: tax_id (MST), social_insurance_id (BHXH number)
    tax_resident = fields.Boolean(
        string='Cư trú thuế',
        default=True,
        groups='hr.group_hr_user',
        help='Không cư trú: áp thuế TNCN 20% flat thay vì biểu lũy tiến.',
    )
    dependent_ids = fields.One2many(
        'hr.vn.dependent', 'employee_id',
        string='Người phụ thuộc',
        groups='hr.group_hr_user',
    )
    dependent_count = fields.Integer(
        string='Số NPT được duyệt',
        compute='_compute_dependent_count',
        groups='hr.group_hr_user',
    )

    @api.depends('dependent_ids.status')
    def _compute_dependent_count(self):
        for emp in self:
            emp.dependent_count = len(
                emp.dependent_ids.filtered(lambda d: d.status == 'approved')
            )
