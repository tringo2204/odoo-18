# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ShtHrHeadcountAllocation(models.Model):
    _name = 'sht.hr.headcount.allocation'
    _description = 'Phân bổ định biên'
    _order = 'target_date, sequence, id'
    _inherit = ['mail.thread']

    plan_id = fields.Many2one(
        'sht.hr.headcount.plan', string='Kế hoạch định biên',
        required=True, ondelete='cascade', index=True,
    )
    sequence = fields.Integer(string='Thứ tự', default=10)
    name = fields.Char(
        string='Tên vị trí / Ghi chú',
        help='Mô tả cụ thể cho slot tuyển dụng này',
    )
    job_id = fields.Many2one(
        'hr.job', string='Vị trí công việc',
        ondelete='restrict',
    )
    department_id = fields.Many2one(
        related='plan_id.department_id', string='Phòng ban', store=True,
    )
    company_id = fields.Many2one(
        related='plan_id.company_id', string='Công ty', store=True,
    )
    count = fields.Integer(
        string='Số lượng cần tuyển', default=1, required=True,
        tracking=True,
    )
    target_date = fields.Date(
        string='Tháng cần có người',
        help='Thời điểm dự kiến cần nhân sự vào vị trí này',
        tracking=True,
    )
    budget_wage = fields.Monetary(
        string='Ngân sách lương/tháng (1 người)',
        currency_field='currency_id',
        help='Mức lương dự kiến cho 1 người ở vị trí này',
    )
    currency_id = fields.Many2one(
        related='company_id.currency_id', string='Tiền tệ',
    )
    total_budget = fields.Monetary(
        string='Tổng ngân sách',
        compute='_compute_total_budget', store=True,
        currency_field='currency_id',
    )
    state = fields.Selection(
        selection=[
            ('open', 'Chưa mở tuyển'),
            ('recruiting', 'Đang tuyển'),
            ('filled', 'Đã điền đủ'),
            ('cancelled', 'Đã hủy'),
        ],
        string='Trạng thái', default='open', required=True,
        tracking=True,
    )
    applicant_ids = fields.Many2many(
        'hr.applicant',
        'sht_headcount_allocation_applicant_rel',
        'allocation_id', 'applicant_id',
        string='Ứng viên đang theo dõi',
        domain="[('department_id', '=', department_id)]",
    )
    applicant_count = fields.Integer(
        string='Số ứng viên', compute='_compute_applicant_count',
    )
    filled_employee_ids = fields.Many2many(
        'hr.employee',
        'sht_headcount_allocation_employee_rel',
        'allocation_id', 'employee_id',
        string='Nhân viên đã tuyển được',
        domain="[('department_id', '=', department_id)]",
    )
    filled_count = fields.Integer(
        string='Đã tuyển được', compute='_compute_filled_count', store=True,
    )
    remaining_count = fields.Integer(
        string='Còn thiếu', compute='_compute_filled_count', store=True,
    )
    note = fields.Text(string='Ghi chú')

    @api.depends('budget_wage', 'count')
    def _compute_total_budget(self):
        for rec in self:
            rec.total_budget = (rec.budget_wage or 0) * (rec.count or 0)

    @api.depends('applicant_ids')
    def _compute_applicant_count(self):
        for rec in self:
            rec.applicant_count = len(rec.applicant_ids)

    @api.depends('filled_employee_ids', 'count')
    def _compute_filled_count(self):
        for rec in self:
            rec.filled_count = len(rec.filled_employee_ids)
            rec.remaining_count = max(rec.count - rec.filled_count, 0)

    @api.onchange('filled_employee_ids', 'count')
    def _onchange_auto_state(self):
        for rec in self:
            if rec.state == 'cancelled':
                continue
            filled = len(rec.filled_employee_ids)
            if filled >= (rec.count or 1):
                rec.state = 'filled'
            elif filled > 0 or rec.applicant_ids:
                rec.state = 'recruiting'

    def action_start_recruiting(self):
        for rec in self:
            if rec.state != 'open':
                raise UserError(_('Chỉ mở tuyển slot ở trạng thái "Chưa mở tuyển".'))
        self.write({'state': 'recruiting'})

    def action_mark_filled(self):
        self.write({'state': 'filled'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reopen(self):
        self.write({'state': 'open'})

    def action_view_applicants(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Ứng viên — %s') % (self.name or self.job_id.name or ''),
            'res_model': 'hr.applicant',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.applicant_ids.ids)],
            'context': {
                'default_department_id': self.department_id.id,
                'default_job_id': self.job_id.id,
            },
        }
