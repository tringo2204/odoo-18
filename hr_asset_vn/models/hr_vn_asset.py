from odoo import api, fields, models


class HrVnAsset(models.Model):
    _name = 'hr.vn.asset'
    _description = 'Tài sản'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'code'
    _check_company_auto = True

    name = fields.Char(string='Tên tài sản', required=True, tracking=True)
    code = fields.Char(string='Mã tài sản', readonly=True, copy=False, default='Mới')
    category_id = fields.Many2one(
        'hr.vn.asset.category', string='Danh mục', required=True,
        ondelete='restrict',
    )
    serial_number = fields.Char(string='Số serial')
    purchase_date = fields.Date(string='Ngày mua')
    purchase_value = fields.Float(string='Giá trị ban đầu')
    depreciation_years = fields.Integer(
        string='Số năm khấu hao',
        related='category_id.depreciation_years', readonly=False, store=True,
    )
    monthly_depreciation = fields.Float(
        string='Khấu hao tháng', compute='_compute_depreciation', store=True,
    )
    accumulated_depreciation = fields.Float(
        string='Khấu hao lũy kế', compute='_compute_depreciation', store=True,
    )
    residual_value = fields.Float(
        string='Giá trị còn lại', compute='_compute_depreciation', store=True,
    )
    state = fields.Selection([
        ('available', 'Sẵn có'),
        ('allocated', 'Đã cấp phát'),
        ('maintenance', 'Bảo trì'),
        ('disposed', 'Đã thanh lý'),
    ], string='Trạng thái', default='available', tracking=True)

    current_employee_id = fields.Many2one(
        'hr.employee', string='Người đang giữ', readonly=True,
    )
    current_department_id = fields.Many2one(
        'hr.department', string='Phòng ban', readonly=True,
    )
    allocation_ids = fields.One2many(
        'hr.vn.asset.allocation', 'asset_id', string='Lịch sử cấp phát/thu hồi',
    )
    allocation_count = fields.Integer(compute='_compute_allocation_count')
    image = fields.Binary(string='Hình ảnh')
    note = fields.Text(string='Ghi chú')
    company_id = fields.Many2one(
        'res.company', string='Công ty', default=lambda self: self.env.company,
    )

    @api.depends('purchase_value', 'depreciation_years', 'purchase_date')
    def _compute_depreciation(self):
        today = fields.Date.today()
        for rec in self:
            if rec.purchase_value and rec.depreciation_years and rec.purchase_date:
                total_months = rec.depreciation_years * 12
                rec.monthly_depreciation = rec.purchase_value / total_months if total_months else 0
                months_used = (today.year - rec.purchase_date.year) * 12 + (today.month - rec.purchase_date.month)
                months_used = max(0, min(months_used, total_months))
                rec.accumulated_depreciation = rec.monthly_depreciation * months_used
                rec.residual_value = rec.purchase_value - rec.accumulated_depreciation
            else:
                rec.monthly_depreciation = 0
                rec.accumulated_depreciation = 0
                rec.residual_value = rec.purchase_value or 0

    @api.depends('allocation_ids')
    def _compute_allocation_count(self):
        for rec in self:
            rec.allocation_count = len(rec.allocation_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('code', 'Mới') == 'Mới':
                vals['code'] = self.env['ir.sequence'].next_by_code('hr.vn.asset') or 'Mới'
        return super().create(vals_list)

    def action_allocate(self):
        """Open wizard / quick form to allocate asset."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Cấp phát tài sản',
            'res_model': 'hr.vn.asset.allocation',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_asset_id': self.id,
                'default_allocation_type': 'allocate',
            },
        }

    def action_return(self):
        """Open wizard to return asset."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Thu hồi tài sản',
            'res_model': 'hr.vn.asset.allocation',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_asset_id': self.id,
                'default_allocation_type': 'return',
                'default_employee_id': self.current_employee_id.id,
            },
        }

    def action_dispose(self):
        self.write({'state': 'disposed'})

    def action_maintenance(self):
        self.write({'state': 'maintenance'})

    def action_available(self):
        self.write({'state': 'available', 'current_employee_id': False, 'current_department_id': False})
