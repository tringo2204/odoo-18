# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ShtHrTraining(models.Model):
    _name = 'sht.hr.training'
    _description = 'Employee Training Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc, id desc'

    name = fields.Char(compute='_compute_name', store=True)
    employee_id = fields.Many2one(
        'hr.employee',
        required=True,
        ondelete='cascade',
    )
    department_id = fields.Many2one(
        'hr.department',
        related='employee_id.department_id',
        store=True,
        readonly=True,
    )
    course_id = fields.Many2one(
        'sht.hr.training.course',
        required=True,
        ondelete='restrict',
    )
    date_start = fields.Date(required=True)
    date_end = fields.Date()
    state = fields.Selection(
        [
            ('planned', 'Planned'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled'),
        ],
        default='planned',
        tracking=True,
    )
    result = fields.Selection(
        [
            ('pass', 'Pass'),
            ('fail', 'Fail'),
            ('na', 'N/A'),
        ],
        default='na',
    )
    score = fields.Float()
    certificate_attachment = fields.Binary(attachment=True)
    certificate_filename = fields.Char()
    note = fields.Text()
    cost = fields.Float(string='Cost (VND)')
    plan_id = fields.Many2one(
        'sht.hr.training.plan', string='Kế hoạch đào tạo',
        ondelete='set null',
    )
    commitment_months = fields.Integer(
        string='Cam kết (tháng)',
        help='Số tháng NV cam kết làm việc sau đào tạo',
    )
    commitment_end_date = fields.Date(
        string='Hết cam kết', compute='_compute_commitment_end',
    )
    evaluation_level = fields.Selection([
        ('1_reaction', 'L1 — Phản hồi'),
        ('2_learning', 'L2 — Kiến thức'),
        ('3_behavior', 'L3 — Hành vi'),
        ('4_results', 'L4 — Kết quả'),
    ], string='Mức đánh giá (Kirkpatrick)')
    evaluation_score = fields.Float(string='Điểm đánh giá (1-5)')
    evaluation_note = fields.Text(string='Nhận xét đánh giá')
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        required=True,
    )

    @api.depends('course_id', 'employee_id')
    def _compute_name(self):
        for rec in self:
            parts = []
            if rec.course_id:
                parts.append(rec.course_id.name or '')
            if rec.employee_id:
                parts.append(rec.employee_id.name or '')
            rec.name = ' - '.join(parts) if parts else ''

    @api.constrains('date_start', 'date_end')
    def _check_date_end(self):
        for rec in self:
            if rec.date_start and rec.date_end and rec.date_end < rec.date_start:
                raise ValidationError(
                    _('End date must be on or after the start date.')
                )

    @api.depends('date_end', 'commitment_months')
    def _compute_commitment_end(self):
        from dateutil.relativedelta import relativedelta
        for rec in self:
            if rec.date_end and rec.commitment_months:
                rec.commitment_end_date = rec.date_end + relativedelta(months=rec.commitment_months)
            else:
                rec.commitment_end_date = False

    def action_start(self):
        self.write({'state': 'in_progress'})
        for rec in self:
            rec._notify_participant(_('Khóa đào tạo "%s" đã bắt đầu.') % rec.course_id.name)

    def action_complete(self):
        self.write({'state': 'completed'})
        for rec in self:
            rec._notify_participant(_('Khóa đào tạo "%s" đã hoàn thành.') % rec.course_id.name)

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def _notify_participant(self, message):
        """Thông báo cho nhân viên tham gia đào tạo."""
        self.ensure_one()
        if self.employee_id and self.employee_id.user_id:
            self.activity_schedule(
                act_type_xmlid='mail.mail_activity_data_todo',
                summary=message[:100],
                user_id=self.employee_id.user_id.id,
            )
