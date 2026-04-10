from odoo import api, fields, models


class ShtHrAppraisalLine(models.Model):
    _name = 'sht.hr.appraisal.line'
    _description = 'Dòng đánh giá chi tiết'
    _order = 'criteria_id'

    appraisal_id = fields.Many2one(
        'hr.appraisal', string='Phiếu đánh giá',
        required=True, ondelete='cascade',
    )
    criteria_id = fields.Many2one(
        'sht.hr.appraisal.criteria', string='Tiêu chí',
        required=True,
    )
    category = fields.Selection(
        related='criteria_id.category', store=True, string='Nhóm',
    )
    weight = fields.Float(string='Trọng số (%)')
    self_score = fields.Float(string='Tự đánh giá (1-5)', default=0)
    manager_score = fields.Float(string='Quản lý đánh giá (1-5)', default=0)
    final_score = fields.Float(
        string='Điểm cuối', compute='_compute_final_score', store=True,
    )
    note = fields.Text(string='Nhận xét')

    @api.depends('self_score', 'manager_score')
    def _compute_final_score(self):
        for line in self:
            if line.manager_score:
                line.final_score = line.manager_score
            else:
                line.final_score = line.self_score
