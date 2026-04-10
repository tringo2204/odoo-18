from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrKpiTemplate(models.Model):
    _name = 'hr.kpi.template'
    _description = 'Mẫu KPI'
    _order = 'name'
    _check_company_auto = True

    name = fields.Char(string='Tên mẫu', required=True)
    department_id = fields.Many2one('hr.department', string='Phòng ban')
    job_id = fields.Many2one('hr.job', string='Chức danh')
    criteria_ids = fields.Many2many(
        'hr.kpi.criteria', 'hr_kpi_template_criteria_rel',
        'template_id', 'criteria_id', string='Tiêu chí',
    )
    total_weight = fields.Float(
        string='Tổng trọng số', compute='_compute_total_weight', store=True,
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', string='Công ty',
        default=lambda self: self.env.company,
    )

    @api.depends('criteria_ids.weight')
    def _compute_total_weight(self):
        for rec in self:
            rec.total_weight = sum(rec.criteria_ids.mapped('weight'))

    @api.constrains('criteria_ids')
    def _check_weight(self):
        for rec in self:
            if rec.criteria_ids and abs(rec.total_weight - 100.0) > 0.01:
                raise ValidationError(
                    _('Tổng trọng số phải = 100%%. Hiện tại: %.1f%%') % rec.total_weight
                )
