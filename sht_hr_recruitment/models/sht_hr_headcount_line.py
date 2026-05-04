# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


MONTHS = [
    ('1', 'Tháng 1'), ('2', 'Tháng 2'), ('3', 'Tháng 3'),
    ('4', 'Tháng 4'), ('5', 'Tháng 5'), ('6', 'Tháng 6'),
    ('7', 'Tháng 7'), ('8', 'Tháng 8'), ('9', 'Tháng 9'),
    ('10', 'Tháng 10'), ('11', 'Tháng 11'), ('12', 'Tháng 12'),
]


class ShtHrHeadcountLine(models.Model):
    """
    Bảng định biên nhân sự kiểu 1Office:
    Mỗi record = 1 ô trong bảng (1 Phòng ban + 1 Vị trí + 1 Năm + 1 Tháng).
    Pivot view: rows = Phòng ban + Vị trí, cols = Năm + Tháng,
                measures = ĐB (định biên) / NS (hiện tại) / CT (còn thiếu).
    """
    _name = 'sht.hr.headcount.line'
    _description = 'Bảng định biên nhân sự'
    _order = 'year desc, month, department_id, job_id'
    _rec_name = 'display_name'
    _inherit = ['mail.thread']

    # ── Dimensions ────────────────────────────────────────────────────────────
    department_id = fields.Many2one(
        'hr.department', string='Phòng ban',
        required=True, ondelete='restrict', tracking=True, index=True,
    )
    job_id = fields.Many2one(
        'hr.job', string='Vị trí công việc',
        required=True, ondelete='restrict', tracking=True,
    )
    year = fields.Integer(
        string='Năm', required=True,
        default=lambda self: fields.Date.today().year,
        group_operator='max',
    )
    month = fields.Selection(
        MONTHS, string='Tháng', required=True,
        default=lambda self: str(fields.Date.today().month),
    )
    company_id = fields.Many2one(
        'res.company', string='Công ty', required=True,
        default=lambda self: self.env.company,
    )

    # ── ĐB: Định biên (planned) ───────────────────────────────────────────────
    planned_count = fields.Integer(
        string='Số lượng định biên', default=0, required=True,
        tracking=True, group_operator='sum',
        help='Số lượng nhân sự định biên cho tháng này',
    )

    # ── Nhân sự hiện tại (actual) ─────────────────────────────────────────────
    current_count = fields.Integer(
        string='Nhân sự hiện tại',
        compute='_compute_current_count',
        store=True, group_operator='sum',
        help='Số nhân viên đang hoạt động tại vị trí này',
    )

    # ── Còn thiếu (gap) ───────────────────────────────────────────────────────
    gap = fields.Integer(
        string='Còn thiếu',
        compute='_compute_gap',
        store=True, group_operator='sum',
        help='Định biên − Nhân sự hiện tại. Âm = thừa nhân sự, dương = còn thiếu',
    )

    # ── State ─────────────────────────────────────────────────────────────────
    state = fields.Selection(
        selection=[
            ('draft', 'Chưa duyệt'),
            ('approved', 'Đã duyệt'),
            ('cancelled', 'Không áp dụng'),
        ],
        string='Trạng thái', default='draft', required=True,
        tracking=True,
    )
    approved_by = fields.Many2one(
        'res.users', string='Người duyệt', readonly=True,
    )
    approved_date = fields.Date(string='Ngày duyệt', readonly=True)

    note = fields.Char(string='Ghi chú')

    # ── Display ───────────────────────────────────────────────────────────────
    display_name = fields.Char(
        string='Tên', compute='_compute_display_name', store=True,
    )

    # ── Constraints ───────────────────────────────────────────────────────────
    _sql_constraints = [
        (
            'unique_dept_job_year_month',
            'UNIQUE(department_id, job_id, year, month, company_id)',
            'Đã tồn tại dòng định biên cho phòng ban + vị trí + tháng + năm này.',
        ),
    ]

    @api.constrains('planned_count')
    def _check_planned_count(self):
        for rec in self:
            if rec.planned_count < 0:
                raise ValidationError(_('Số lượng định biên không được âm.'))

    # ── Computes ──────────────────────────────────────────────────────────────
    @api.depends('department_id', 'job_id', 'company_id')
    def _compute_current_count(self):
        Employee = self.env['hr.employee']
        for rec in self:
            if not rec.department_id or not rec.job_id:
                rec.current_count = 0
                continue
            rec.current_count = Employee.search_count([
                ('active', '=', True),
                ('department_id', '=', rec.department_id.id),
                ('job_id', '=', rec.job_id.id),
                ('company_id', '=', rec.company_id.id),
            ])

    @api.depends('planned_count', 'current_count')
    def _compute_gap(self):
        for rec in self:
            rec.gap = rec.planned_count - rec.current_count

    @api.depends('department_id', 'job_id', 'year', 'month')
    def _compute_display_name(self):
        month_label = dict(MONTHS)
        for rec in self:
            dept = rec.department_id.name or ''
            job = rec.job_id.name or ''
            mon = month_label.get(rec.month, rec.month)
            rec.display_name = f'{dept} / {job} — {mon} {rec.year}'

    # ── Actions ───────────────────────────────────────────────────────────────
    def action_approve(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Chỉ duyệt dòng định biên ở trạng thái "Chưa duyệt".'))
        self.write({
            'state': 'approved',
            'approved_by': self.env.user.id,
            'approved_date': fields.Date.today(),
        })

    def action_reset_draft(self):
        self.write({'state': 'draft', 'approved_by': False, 'approved_date': False})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    # ── Helpers ───────────────────────────────────────────────────────────────
    @api.model
    def generate_year_plan(self, year, department_ids=None, job_ids=None):
        """
        Tạo 12 dòng định biên (T1–T12) cho mỗi tổ hợp phòng ban + vị trí.
        Nếu đã tồn tại thì bỏ qua (unique constraint).
        """
        departments = (
            self.env['hr.department'].browse(department_ids)
            if department_ids
            else self.env['hr.department'].search([])
        )
        jobs = (
            self.env['hr.job'].browse(job_ids)
            if job_ids
            else self.env['hr.job'].search([])
        )
        created = 0
        for dept in departments:
            for job in jobs:
                for m in range(1, 13):
                    existing = self.search([
                        ('department_id', '=', dept.id),
                        ('job_id', '=', job.id),
                        ('year', '=', year),
                        ('month', '=', str(m)),
                        ('company_id', '=', self.env.company.id),
                    ], limit=1)
                    if not existing:
                        self.create({
                            'department_id': dept.id,
                            'job_id': job.id,
                            'year': year,
                            'month': str(m),
                            'company_id': self.env.company.id,
                        })
                        created += 1
        return created
