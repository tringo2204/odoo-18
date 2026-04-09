from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrVnSiRecord(models.Model):
    _name = 'hr.vn.si.record'
    _description = 'Hồ sơ bảo hiểm xã hội'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'registration_date desc, id desc'

    name = fields.Char(
        string='Mã hồ sơ', readonly=True, copy=False, default='Mới',
    )
    employee_id = fields.Many2one(
        'hr.employee', string='Nhân viên', required=True,
        tracking=True, ondelete='restrict',
    )
    bhxh_number = fields.Char(
        string='Số sổ BHXH',
        related='employee_id.social_insurance_id',
        store=True, readonly=False,
    )
    bhyt_card_number = fields.Char(string='Số thẻ BHYT', tracking=True)
    bhyt_hospital_id = fields.Char(string='Nơi KCB ban đầu', tracking=True)
    registration_date = fields.Date(
        string='Ngày đăng ký', default=fields.Date.today, tracking=True,
    )
    current_status = fields.Selection([
        ('active', 'Đang tham gia'),
        ('suspended', 'Tạm dừng'),
        ('closed', 'Đã chốt sổ'),
    ], string='Trạng thái', default='active', tracking=True)
    insurance_salary = fields.Float(
        string='Mức lương đóng BH', tracking=True,
    )
    department_id = fields.Many2one(
        'hr.department', string='Phòng ban',
        related='employee_id.department_id', store=True,
    )
    company_id = fields.Many2one(
        'res.company', string='Công ty',
        default=lambda self: self.env.company,
    )
    history_ids = fields.One2many(
        'hr.vn.si.history', 'record_id', string='Lịch sử biến động',
    )
    history_count = fields.Integer(
        string='Số biến động', compute='_compute_history_count',
    )
    note = fields.Text(string='Ghi chú')

    _sql_constraints = [
        ('employee_company_uniq',
         'unique(employee_id, company_id)',
         'Mỗi nhân viên chỉ có một hồ sơ bảo hiểm trong cùng công ty.'),
    ]

    @api.depends('history_ids')
    def _compute_history_count(self):
        for rec in self:
            rec.history_count = len(rec.history_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Mới') == 'Mới':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'hr.vn.si.record',
                ) or 'Mới'
        return super().create(vals_list)

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id and self.employee_id.contract_id:
            self.insurance_salary = (
                self.employee_id.contract_id.insurance_salary
                or self.employee_id.contract_id.wage
            )

    def action_activate(self):
        self.write({'current_status': 'active'})

    def action_suspend(self):
        self.write({'current_status': 'suspended'})

    def action_close(self):
        self.write({'current_status': 'closed'})

    def action_open_history(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Lịch sử biến động'),
            'res_model': 'hr.vn.si.history',
            'view_mode': 'list,form',
            'domain': [('record_id', '=', self.id)],
            'context': {'default_record_id': self.id},
        }

    def action_create_increase(self):
        """Tạo biến động tăng mới cho hồ sơ này."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Tạo biến động tăng'),
            'res_model': 'hr.vn.si.history',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_record_id': self.id,
                'default_change_type': 'increase',
                'default_new_salary': self.insurance_salary,
                'default_effective_date': fields.Date.today(),
            },
        }
