# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.translate import _


class ShtHrHealthRecord(models.Model):
    _name = 'sht.hr.health.record'
    _description = 'Hồ sơ khám sức khoẻ nhân viên'
    _order = 'examination_date desc, id desc'
    _rec_name = 'display_name'

    name = fields.Char(
        string='Mã hồ sơ', readonly=True, copy=False,
        default='New',
    )
    employee_id = fields.Many2one(
        'hr.employee', string='Nhân viên', required=True, ondelete='cascade',
        index=True,
    )
    department_id = fields.Many2one(
        related='employee_id.department_id', string='Phòng ban', store=True,
    )
    job_id = fields.Many2one(
        related='employee_id.job_id', string='Chức danh', store=True,
    )
    company_id = fields.Many2one(
        'res.company', string='Công ty', required=True,
        default=lambda self: self.env.company,
    )
    examination_date = fields.Date(
        string='Ngày khám', required=True, default=fields.Date.today,
    )
    clinic = fields.Char(string='Cơ sở y tế')
    doctor_name = fields.Char(string='Bác sĩ khám')

    # Vital signs
    height = fields.Float(string='Chiều cao (cm)', digits=(5, 1))
    weight = fields.Float(string='Cân nặng (kg)', digits=(5, 1))
    bmi = fields.Float(
        string='BMI', compute='_compute_bmi', store=True, digits=(5, 2),
    )
    blood_pressure_systolic = fields.Integer(string='Huyết áp tâm thu (mmHg)')
    blood_pressure_diastolic = fields.Integer(string='Huyết áp tâm trương (mmHg)')
    heart_rate = fields.Integer(string='Nhịp tim (bpm)')
    blood_type = fields.Selection([
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
        ('O+', 'O+'), ('O-', 'O-'),
    ], string='Nhóm máu')

    # Assessment
    vision_left = fields.Char(string='Thị lực mắt trái')
    vision_right = fields.Char(string='Thị lực mắt phải')
    hearing = fields.Selection([
        ('normal', 'Bình thường'),
        ('mild_loss', 'Giảm nhẹ'),
        ('moderate_loss', 'Giảm vừa'),
        ('severe_loss', 'Giảm nặng'),
    ], string='Thính lực')

    result = fields.Selection([
        ('fit', 'Đủ sức khoẻ'),
        ('conditional', 'Đủ sức khoẻ (có điều kiện)'),
        ('follow_up', 'Cần theo dõi'),
        ('unfit', 'Không đủ sức khoẻ'),
    ], string='Kết luận sức khoẻ', required=True, default='fit')

    notes = fields.Text(string='Ghi chú / Chẩn đoán')
    next_examination_date = fields.Date(string='Ngày khám tiếp theo')

    state = fields.Selection([
        ('draft', 'Nháp'),
        ('done', 'Hoàn thành'),
    ], string='Trạng thái', default='draft', required=True)

    attachment_ids = fields.Many2many(
        'ir.attachment', string='Tài liệu đính kèm',
        help='Kết quả xét nghiệm, phim X-quang, v.v.',
    )
    attachment_count = fields.Integer(
        string='Số tài liệu', compute='_compute_attachment_count',
    )

    @api.depends('height', 'weight')
    def _compute_bmi(self):
        for rec in self:
            if rec.height and rec.weight:
                height_m = rec.height / 100.0
                rec.bmi = rec.weight / (height_m ** 2)
            else:
                rec.bmi = 0.0

    @api.depends('attachment_ids')
    def _compute_attachment_count(self):
        for rec in self:
            rec.attachment_count = len(rec.attachment_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'sht.hr.health.record'
                ) or 'New'
        return super().create(vals_list)

    def action_confirm(self):
        self.write({'state': 'done'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    @api.constrains('height')
    def _check_height(self):
        for rec in self:
            if rec.height and (rec.height < 50 or rec.height > 250):
                raise ValidationError(_(
                    'Chiều cao phải nằm trong khoảng 50–250 cm.'
                ))

    @api.constrains('weight')
    def _check_weight(self):
        for rec in self:
            if rec.weight and (rec.weight < 10 or rec.weight > 300):
                raise ValidationError(_(
                    'Cân nặng phải nằm trong khoảng 10–300 kg.'
                ))
