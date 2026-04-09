from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrVnSiHistory(models.Model):
    _name = 'hr.vn.si.history'
    _description = 'Lịch sử biến động BHXH'
    _inherit = ['mail.thread']
    _order = 'effective_date desc, id desc'

    record_id = fields.Many2one(
        'hr.vn.si.record', string='Hồ sơ BH', required=True,
        ondelete='cascade', tracking=True,
    )
    employee_id = fields.Many2one(
        'hr.employee', string='Nhân viên',
        related='record_id.employee_id', store=True,
    )
    bhxh_number = fields.Char(
        string='Số sổ BHXH',
        related='record_id.bhxh_number', store=True,
    )
    change_type = fields.Selection([
        ('increase', 'Tăng'),
        ('decrease', 'Giảm'),
        ('adjust', 'Điều chỉnh'),
        ('sick', 'Ốm đau'),
        ('maternity', 'Thai sản'),
    ], string='Loại biến động', required=True, tracking=True)
    effective_date = fields.Date(
        string='Ngày hiệu lực', required=True, tracking=True,
    )
    old_salary = fields.Float(string='Mức lương cũ')
    new_salary = fields.Float(string='Mức lương mới')
    reason = fields.Char(string='Lý do')
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('confirmed', 'Đã xác nhận'),
        ('reported', 'Đã báo cáo'),
    ], string='Trạng thái', default='draft', tracking=True)
    d02_line_id = fields.Many2one(
        'hr.vn.si.d02.line', string='Dòng D02-LT',
        readonly=True, ondelete='set null',
    )
    company_id = fields.Many2one(
        'res.company', string='Công ty',
        related='record_id.company_id', store=True,
    )
    note = fields.Text(string='Ghi chú')

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Chỉ xác nhận biến động ở trạng thái Nháp.'))
        self.write({'state': 'confirmed'})

    def action_draft(self):
        for rec in self:
            if rec.state == 'reported':
                raise UserError(
                    _('Không thể chuyển về Nháp khi đã báo cáo.')
                )
        self.write({'state': 'draft'})

    def _mark_reported(self, d02_line):
        """Đánh dấu đã báo cáo và liên kết dòng D02."""
        self.write({
            'state': 'reported',
            'd02_line_id': d02_line.id if d02_line else False,
        })

    @api.onchange('record_id')
    def _onchange_record_id(self):
        if self.record_id:
            self.old_salary = self.record_id.insurance_salary
