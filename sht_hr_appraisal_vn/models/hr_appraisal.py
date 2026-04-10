from odoo import api, fields, models


class HrAppraisal(models.Model):
    _inherit = 'hr.appraisal'

    appraisal_cycle_id = fields.Many2one(
        'sht.hr.appraisal.cycle', string='Kỳ đánh giá',
        ondelete='set null',
    )
    sht_template_id = fields.Many2one(
        'sht.hr.appraisal.template', string='Mẫu đánh giá',
    )
    line_ids = fields.One2many(
        'sht.hr.appraisal.line', 'appraisal_id',
        string='Chi tiết đánh giá',
    )
    overall_score = fields.Float(
        string='Điểm tổng', compute='_compute_overall_score', store=True,
    )
    rating = fields.Selection([
        ('excellent', 'Xuất sắc'),
        ('good', 'Tốt'),
        ('meet', 'Đạt'),
        ('improve', 'Cần cải thiện'),
    ], string='Xếp loại', compute='_compute_overall_score', store=True)
    evaluator_type = fields.Selection([
        ('self', 'Tự đánh giá'),
        ('manager', 'Quản lý đánh giá'),
        ('360', 'Đánh giá 360°'),
    ], string='Hình thức', default='manager')

    @api.depends('line_ids.final_score', 'line_ids.weight')
    def _compute_overall_score(self):
        for rec in self:
            lines = rec.line_ids
            if not lines:
                rec.overall_score = 0
                rec.rating = False
                continue
            total_weight = sum(lines.mapped('weight'))
            if total_weight:
                rec.overall_score = sum(
                    l.final_score * l.weight for l in lines
                ) / total_weight
            else:
                rec.overall_score = (
                    sum(lines.mapped('final_score')) / len(lines)
                    if lines else 0
                )
            score = rec.overall_score
            if score >= 4.5:
                rec.rating = 'excellent'
            elif score >= 3.5:
                rec.rating = 'good'
            elif score >= 2.5:
                rec.rating = 'meet'
            else:
                rec.rating = 'improve'

    @api.onchange('sht_template_id')
    def _onchange_template(self):
        if self.sht_template_id and not self.line_ids:
            self._generate_lines_from_template()

    def _generate_lines_from_template(self):
        """Tạo dòng đánh giá từ mẫu."""
        self.ensure_one()
        if not self.sht_template_id:
            return
        # Xóa dòng cũ
        self.line_ids.unlink()
        for criteria in self.sht_template_id.criteria_ids:
            self.env['sht.hr.appraisal.line'].create({
                'appraisal_id': self.id,
                'criteria_id': criteria.id,
                'weight': criteria.weight,
            })
