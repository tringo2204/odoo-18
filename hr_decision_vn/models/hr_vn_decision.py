from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrVnDecision(models.Model):
    _name = 'hr.vn.decision'
    _description = 'Quyết định nhân sự'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'effective_date desc, id desc'
    _check_company_auto = True

    name = fields.Char(
        string='Số quyết định',
        readonly=True,
        copy=False,
        default='Mới',
    )
    decision_type = fields.Selection(
        selection=[
            ('reception', 'Tiếp nhận'),
            ('appointment', 'Bổ nhiệm'),
            ('transfer', 'Điều chuyển'),
            ('salary_adjustment', 'Điều chỉnh lương'),
            ('reward', 'Khen thưởng'),
            ('discipline', 'Kỷ luật'),
            ('dismissal', 'Miễn nhiệm'),
            ('termination', 'Chấm dứt HĐ'),
        ],
        string='Loại quyết định',
        required=True,
        tracking=True,
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Nhân viên',
        required=True,
        tracking=True,
        ondelete='restrict',
        index=True,
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Phòng ban mới',
        help='Phòng ban mới khi điều chuyển',
    )
    job_id = fields.Many2one(
        'hr.job',
        string='Chức danh mới',
        help='Chức danh mới khi bổ nhiệm / điều chuyển',
    )
    old_wage = fields.Float(string='Lương cũ')
    new_wage = fields.Float(string='Lương mới')
    effective_date = fields.Date(
        string='Ngày hiệu lực',
        required=True,
        tracking=True,
    )
    attachment_ids = fields.Many2many(
        'ir.attachment',
        string='Tài liệu đính kèm',
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Nháp'),
            ('confirmed', 'Đã xác nhận'),
            ('done', 'Có hiệu lực'),
            ('cancelled', 'Đã hủy'),
        ],
        string='Trạng thái',
        default='draft',
        tracking=True,
    )
    note = fields.Html(string='Ghi chú')
    company_id = fields.Many2one(
        'res.company',
        string='Công ty',
        default=lambda self: self.env.company,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Mới') == 'Mới':
                vals['name'] = self.env['ir.sequence'].next_by_code('hr.vn.decision') or 'Mới'
        return super().create(vals_list)

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_done(self):
        for rec in self:
            rec._apply_decision()
        self.write({'state': 'done'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_draft(self):
        self.write({'state': 'draft'})

    def _apply_decision(self):
        """Tự động cập nhật hr.employee / hr.contract khi quyết định có hiệu lực."""
        self.ensure_one()
        employee = self.employee_id

        if self.decision_type == 'transfer':
            vals = {}
            if self.department_id:
                vals['department_id'] = self.department_id.id
            if self.job_id:
                vals['job_id'] = self.job_id.id
            if vals:
                employee.write(vals)

        elif self.decision_type == 'appointment':
            if self.job_id:
                employee.write({'job_id': self.job_id.id})

        elif self.decision_type == 'salary_adjustment':
            contract = employee.contract_id
            if not contract:
                raise UserError(_(
                    'Nhân viên %s không có hợp đồng đang hiệu lực.',
                    employee.name,
                ))
            contract.write({'wage': self.new_wage})

        elif self.decision_type == 'termination':
            employee.write({
                'departure_date': self.effective_date,
            })

    @api.onchange('decision_type', 'employee_id')
    def _onchange_populate_wage(self):
        if self.decision_type == 'salary_adjustment' and self.employee_id:
            contract = self.employee_id.contract_id
            self.old_wage = contract.wage if contract else 0.0
