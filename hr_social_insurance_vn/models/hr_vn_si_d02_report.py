from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrVnSiD02Report(models.Model):
    _name = 'hr.vn.si.d02.report'
    _description = 'Báo cáo D02-LT (Biến động lao động)'
    _inherit = ['mail.thread']
    _order = 'year desc, month desc'
    _check_company_auto = True

    name = fields.Char(
        string='Số báo cáo', readonly=True, copy=False, default='Mới',
    )
    month = fields.Selection([
        ('1', 'Tháng 1'), ('2', 'Tháng 2'), ('3', 'Tháng 3'),
        ('4', 'Tháng 4'), ('5', 'Tháng 5'), ('6', 'Tháng 6'),
        ('7', 'Tháng 7'), ('8', 'Tháng 8'), ('9', 'Tháng 9'),
        ('10', 'Tháng 10'), ('11', 'Tháng 11'), ('12', 'Tháng 12'),
    ], string='Tháng', required=True, tracking=True)
    year = fields.Integer(string='Năm', required=True, tracking=True)
    company_id = fields.Many2one(
        'res.company', string='Công ty',
        default=lambda self: self.env.company,
    )
    monthly_list_id = fields.Many2one(
        'hr.vn.si.monthly.list', string='DS tăng/giảm tháng',
        readonly=True,
    )
    line_ids = fields.One2many(
        'hr.vn.si.d02.line', 'report_id', string='Chi tiết biến động',
    )
    line_count = fields.Integer(
        string='Số dòng', compute='_compute_line_count',
    )
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('confirmed', 'Đã xác nhận'),
        ('submitted', 'Đã nộp'),
    ], string='Trạng thái', default='draft', tracking=True)
    export_file = fields.Binary(string='File xuất', readonly=True)
    export_filename = fields.Char(string='Tên file')
    note = fields.Text(string='Ghi chú')

    @api.depends('line_ids')
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Mới') == 'Mới':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'hr.vn.si.d02.report',
                ) or 'Mới'
        return super().create(vals_list)

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(
                    _('Chỉ xác nhận báo cáo ở trạng thái Nháp.')
                )
            if not rec.line_ids:
                raise UserError(_('Báo cáo chưa có dòng chi tiết.'))
        self.write({'state': 'confirmed'})

    def action_submit(self):
        for rec in self:
            if rec.state != 'confirmed':
                raise UserError(
                    _('Phải xác nhận báo cáo trước khi nộp.')
                )
        self.write({'state': 'submitted'})

    def action_draft(self):
        for rec in self:
            if rec.state == 'submitted':
                raise UserError(
                    _('Không thể chuyển về Nháp khi đã nộp.')
                )
        self.write({'state': 'draft'})

    def action_generate_lines(self):
        """Tạo/cập nhật dòng D02 từ danh sách tăng/giảm liên kết."""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Chỉ tạo dòng khi báo cáo ở trạng thái Nháp.'))
        if not self.monthly_list_id:
            raise UserError(_('Chưa liên kết danh sách tăng/giảm tháng.'))
        # Xóa dòng cũ
        self.line_ids.unlink()
        # Tạo dòng mới từ history confirmed
        history_entries = self.monthly_list_id.history_ids.filtered(
            lambda h: h.state in ('confirmed', 'reported')
            and h.change_type in ('increase', 'decrease', 'adjust')
        )
        D02Line = self.env['hr.vn.si.d02.line']
        line_vals_list = []
        for entry in history_entries:
            line_vals_list.append({
                'report_id': self.id,
                'employee_id': entry.employee_id.id,
                'bhxh_number': entry.bhxh_number or '',
                'full_name': entry.employee_id.name,
                'change_type': entry.change_type,
                'old_salary': entry.old_salary,
                'new_salary': entry.new_salary,
                'effective_date': entry.effective_date,
            })
        lines = D02Line.create(line_vals_list)
        for entry, line in zip(history_entries, lines):
            entry._mark_reported(line)
        # Cập nhật trạng thái monthly list
        if self.monthly_list_id.state == 'confirmed':
            self.monthly_list_id.write({'state': 'exported'})
