# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ShtHrTrainingPlan(models.Model):
    _name = 'sht.hr.training.plan'
    _description = 'Kế hoạch đào tạo'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'year desc, name'
    _check_company_auto = True

    name = fields.Char(string='Tên kế hoạch', required=True, tracking=True)
    year = fields.Integer(
        string='Năm', required=True,
        default=lambda self: fields.Date.today().year,
    )
    department_ids = fields.Many2many(
        'hr.department', string='Phòng ban áp dụng',
    )
    budget = fields.Float(string='Ngân sách (VND)', tracking=True)
    spent = fields.Float(
        string='Đã chi', compute='_compute_spent', store=True,
    )
    remaining_budget = fields.Float(
        string='Còn lại', compute='_compute_spent', store=True,
    )
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('approved', 'Đã duyệt'),
        ('closed', 'Đã đóng'),
    ], string='Trạng thái', default='draft', tracking=True)
    training_ids = fields.One2many(
        'sht.hr.training', 'plan_id', string='Khóa đào tạo',
    )
    training_count = fields.Integer(compute='_compute_spent')
    company_id = fields.Many2one(
        'res.company', string='Công ty',
        default=lambda self: self.env.company,
    )
    note = fields.Text(string='Ghi chú')

    @api.depends('training_ids.cost', 'budget')
    def _compute_spent(self):
        for rec in self:
            rec.training_count = len(rec.training_ids)
            rec.spent = sum(rec.training_ids.mapped('cost'))
            rec.remaining_budget = rec.budget - rec.spent

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_close(self):
        self.write({'state': 'closed'})

    def action_draft(self):
        self.write({'state': 'draft'})
