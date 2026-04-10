from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ShtHrAppraisalTemplate(models.Model):
    _name = 'sht.hr.appraisal.template'
    _description = 'Mẫu đánh giá'
    _order = 'name'

    name = fields.Char(string='Tên mẫu', required=True)
    job_id = fields.Many2one('hr.job', string='Chức danh')
    department_id = fields.Many2one('hr.department', string='Phòng ban')
    criteria_ids = fields.Many2many(
        'sht.hr.appraisal.criteria',
        'sht_appraisal_template_criteria_rel',
        'template_id', 'criteria_id',
        string='Tiêu chí đánh giá',
    )
    total_weight = fields.Float(
        string='Tổng trọng số (%)',
        compute='_compute_total_weight', store=True,
    )
    active = fields.Boolean(string='Hoạt động', default=True)
    company_id = fields.Many2one(
        'res.company', string='Công ty',
        default=lambda self: self.env.company,
    )
    note = fields.Text(string='Ghi chú')

    @api.depends('criteria_ids.weight')
    def _compute_total_weight(self):
        for rec in self:
            rec.total_weight = sum(rec.criteria_ids.mapped('weight'))

    @api.constrains('criteria_ids')
    def _check_total_weight(self):
        for rec in self:
            if rec.criteria_ids and abs(rec.total_weight - 100.0) > 0.01:
                raise ValidationError(
                    _('Tổng trọng số phải bằng 100%%. Hiện tại: %.1f%%')
                    % rec.total_weight
                )
