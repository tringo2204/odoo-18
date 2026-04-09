from odoo import api, fields, models, _


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    asset_ids = fields.One2many(
        'hr.vn.asset', 'current_employee_id',
        string='Tài sản đang giữ', groups='hr.group_hr_user',
    )
    asset_count = fields.Integer(
        string='Số tài sản', compute='_compute_asset_count',
        groups='hr.group_hr_user',
    )

    @api.depends('asset_ids')
    def _compute_asset_count(self):
        for emp in self:
            emp.asset_count = len(emp.asset_ids)

    def action_open_assets(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Tài sản'),
            'res_model': 'hr.vn.asset',
            'view_mode': 'list,form',
            'domain': [('current_employee_id', '=', self.id)],
        }
