# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.translate import _


class ShtHrApplicantEvaluation(models.Model):
    _name = 'sht.hr.applicant.evaluation'
    _description = 'Đánh giá ứng viên'
    _order = 'evaluation_date desc'

    applicant_id = fields.Many2one(
        'hr.applicant', string='Ứng viên', required=True, ondelete='cascade',
    )
    evaluator_id = fields.Many2one(
        'res.users', string='Người đánh giá',
        default=lambda self: self.env.user, required=True,
    )
    evaluation_date = fields.Date(
        string='Ngày đánh giá', default=fields.Date.today,
    )
    criteria_ids = fields.One2many(
        'sht.hr.evaluation.criteria', 'evaluation_id',
        string='Tiêu chí đánh giá',
    )
    overall_score = fields.Float(
        string='Điểm tổng', compute='_compute_overall_score', store=True,
    )
    recommendation = fields.Selection([
        ('hire', 'Tuyển'),
        ('reject', 'Từ chối'),
        ('hold', 'Giữ hồ sơ'),
    ], string='Khuyến nghị')
    note = fields.Text(string='Nhận xét')
    company_id = fields.Many2one(
        'res.company', string='Công ty',
        default=lambda self: self.env.company,
    )

    @api.depends('criteria_ids.score', 'criteria_ids.weight')
    def _compute_overall_score(self):
        for rec in self:
            criteria = rec.criteria_ids
            if not criteria:
                rec.overall_score = 0
                continue
            total_weight = sum(criteria.mapped('weight'))
            if total_weight:
                rec.overall_score = sum(
                    c.score * c.weight for c in criteria
                ) / total_weight
            else:
                rec.overall_score = (
                    sum(criteria.mapped('score')) / len(criteria)
                )


class ShtHrEvaluationCriteria(models.Model):
    _name = 'sht.hr.evaluation.criteria'
    _description = 'Tiêu chí đánh giá ứng viên'
    _order = 'sequence'

    evaluation_id = fields.Many2one(
        'sht.hr.applicant.evaluation', string='Đánh giá',
        required=True, ondelete='cascade',
    )
    name = fields.Char(string='Tiêu chí', required=True)
    sequence = fields.Integer(string='Thứ tự', default=10)
    score = fields.Float(string='Điểm (1-5)')
    weight = fields.Float(string='Trọng số', default=1.0)
    note = fields.Text(string='Nhận xét')

    @api.constrains('score')
    def _check_score_range(self):
        for rec in self:
            if rec.score and (rec.score < 1 or rec.score > 5):
                raise ValidationError(_(
                    'Điểm đánh giá phải nằm trong khoảng từ 1 đến 5. '
                    'Vui lòng nhập lại tiêu chí "%s".'
                ) % rec.name)

    @api.onchange('score')
    def _onchange_score_warning(self):
        """Cảnh báo ngay khi user gõ điểm vượt thang 1-5, trước khi save."""
        if self.score and (self.score < 1 or self.score > 5):
            return {
                'warning': {
                    'title': _('Điểm vượt thang tham chiếu'),
                    'message': _(
                        'Điểm đánh giá "%s" = %s nằm ngoài thang 1-5. '
                        'Hệ thống sẽ không ghi nhận giá trị này khi lưu.'
                    ) % (self.name or '', self.score),
                }
            }
