from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrVnAssetAllocation(models.Model):
    _name = 'hr.vn.asset.allocation'
    _description = 'Cấp phát / Thu hồi tài sản'
    _order = 'date desc, id desc'

    asset_id = fields.Many2one(
        'hr.vn.asset', string='Tài sản', required=True, ondelete='cascade',
    )
    employee_id = fields.Many2one('hr.employee', string='Nhân viên', required=True)
    department_id = fields.Many2one(
        'hr.department', string='Phòng ban',
        related='employee_id.department_id', store=True,
    )
    allocation_type = fields.Selection([
        ('allocate', 'Cấp phát'),
        ('return', 'Thu hồi'),
    ], string='Loại', required=True, default='allocate')
    date = fields.Date(string='Ngày', default=fields.Date.today, required=True)
    condition_on_return = fields.Selection([
        ('good', 'Tốt'),
        ('damaged', 'Hư hỏng'),
        ('lost', 'Mất'),
    ], string='Tình trạng khi thu hồi')
    approved_by_id = fields.Many2one('res.users', string='Người duyệt')
    note = fields.Text(string='Ghi chú')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('asset_id') or not vals.get('employee_id'):
                raise UserError(_('Phải chọn tài sản và nhân viên.'))
        records = super().create(vals_list)
        for rec in records:
            rec._update_asset_state()
        return records

    def _update_asset_state(self):
        """Update asset state based on allocation type."""
        self.ensure_one()
        asset = self.asset_id
        if self.allocation_type == 'allocate':
            if asset.state not in ('available', 'maintenance'):
                raise UserError(_('Chỉ cấp phát tài sản đang sẵn có hoặc bảo trì.'))
            asset.write({
                'state': 'allocated',
                'current_employee_id': self.employee_id.id,
                'current_department_id': self.employee_id.department_id.id,
            })
        elif self.allocation_type == 'return':
            new_state = 'available'
            if self.condition_on_return == 'damaged':
                new_state = 'maintenance'
            elif self.condition_on_return == 'lost':
                new_state = 'disposed'
            asset.write({
                'state': new_state,
                'current_employee_id': False,
                'current_department_id': False,
            })
