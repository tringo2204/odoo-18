from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrKpiAssignment(models.Model):
    _name = 'hr.kpi.assignment'
    _description = 'Phân công KPI cá nhân'
    _inherit = ['mail.thread']
    _order = 'period_id desc, employee_id'

    period_id = fields.Many2one(
        'hr.kpi.period', string='Kỳ đánh giá', required=True, ondelete='cascade',
    )
    employee_id = fields.Many2one(
        'hr.employee', string='Nhân viên', required=True, tracking=True,
    )
    department_id = fields.Many2one(
        'hr.department', related='employee_id.department_id', store=True,
    )
    template_id = fields.Many2one('hr.kpi.template', string='Mẫu KPI')
    line_ids = fields.One2many(
        'hr.kpi.assignment.line', 'assignment_id', string='Chi tiết KPI',
    )
    overall_score = fields.Float(
        string='Điểm tổng', compute='_compute_score', store=True,
    )
    rating = fields.Selection([
        ('excellent', 'Xuất sắc (≥90)'),
        ('good', 'Tốt (≥75)'),
        ('meet', 'Đạt (≥60)'),
        ('improve', 'Cần cải thiện (<60)'),
    ], string='Xếp loại', compute='_compute_score', store=True)
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('submitted', 'Đã nộp'),
        ('evaluated', 'Đã đánh giá'),
        ('done', 'Hoàn thành'),
    ], string='Trạng thái', default='draft', tracking=True)
    company_id = fields.Many2one(
        'res.company', related='period_id.company_id', store=True,
    )

    @api.depends('line_ids.score', 'line_ids.weight')
    def _compute_score(self):
        for rec in self:
            lines = rec.line_ids
            if not lines:
                rec.overall_score = 0
                rec.rating = False
                continue
            total_weight = sum(lines.mapped('weight'))
            if total_weight:
                rec.overall_score = sum(l.score * l.weight for l in lines) / total_weight
            else:
                rec.overall_score = sum(lines.mapped('score')) / len(lines) if lines else 0
            s = rec.overall_score
            rec.rating = 'excellent' if s >= 90 else 'good' if s >= 75 else 'meet' if s >= 60 else 'improve'

    def action_submit(self):
        self.write({'state': 'submitted'})

    def action_evaluate(self):
        self.write({'state': 'evaluated'})

    def action_done(self):
        self.write({'state': 'done'})

    def action_draft(self):
        self.write({'state': 'draft'})

    def _generate_lines(self):
        self.ensure_one()
        if not self.template_id:
            return
        self.line_ids.unlink()
        for criteria in self.template_id.criteria_ids:
            self.env['hr.kpi.assignment.line'].create({
                'assignment_id': self.id,
                'criteria_id': criteria.id,
                'weight': criteria.weight,
                'target_value': criteria.target_value,
            })


class HrKpiAssignmentLine(models.Model):
    _name = 'hr.kpi.assignment.line'
    _description = 'Dòng KPI chi tiết'
    _order = 'criteria_id'

    assignment_id = fields.Many2one(
        'hr.kpi.assignment', required=True, ondelete='cascade',
    )
    criteria_id = fields.Many2one(
        'hr.kpi.criteria', string='Tiêu chí', required=True,
    )
    category = fields.Selection(related='criteria_id.category', store=True)
    weight = fields.Float(string='Trọng số (%)')
    target_value = fields.Float(string='Mục tiêu')
    actual_value = fields.Float(string='Thực tế')
    score = fields.Float(
        string='Điểm (%)', compute='_compute_score', store=True,
    )
    note = fields.Text(string='Nhận xét')

    @api.depends('actual_value', 'target_value')
    def _compute_score(self):
        for line in self:
            if line.target_value:
                line.score = min((line.actual_value / line.target_value) * 100, 150)
            else:
                line.score = 0
