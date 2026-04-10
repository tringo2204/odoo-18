from odoo import api, fields, models


class HrOkrObjective(models.Model):
    _name = 'hr.okr.objective'
    _description = 'OKR Objective'
    _inherit = ['mail.thread']
    _order = 'create_date desc'
    _check_company_auto = True

    name = fields.Char(string='Mục tiêu', required=True, tracking=True)
    owner_id = fields.Many2one(
        'hr.employee', string='Người sở hữu', required=True,
    )
    parent_id = fields.Many2one(
        'hr.okr.objective', string='Mục tiêu cấp trên',
        ondelete='set null',
    )
    child_ids = fields.One2many('hr.okr.objective', 'parent_id', string='Mục tiêu con')
    period_id = fields.Many2one('hr.kpi.period', string='Kỳ đánh giá')
    key_result_ids = fields.One2many(
        'hr.okr.key.result', 'objective_id', string='Key Results',
    )
    progress = fields.Float(
        string='Tiến độ (%)', compute='_compute_progress', store=True,
    )
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('active', 'Đang thực hiện'),
        ('done', 'Hoàn thành'),
        ('cancelled', 'Đã hủy'),
    ], string='Trạng thái', default='draft', tracking=True)
    company_id = fields.Many2one(
        'res.company', string='Công ty',
        default=lambda self: self.env.company,
    )

    @api.depends('key_result_ids.progress')
    def _compute_progress(self):
        for obj in self:
            krs = obj.key_result_ids
            obj.progress = sum(krs.mapped('progress')) / len(krs) if krs else 0

    def action_activate(self):
        self.write({'state': 'active'})

    def action_done(self):
        self.write({'state': 'done'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_draft(self):
        self.write({'state': 'draft'})


class HrOkrKeyResult(models.Model):
    _name = 'hr.okr.key.result'
    _description = 'OKR Key Result'
    _order = 'sequence'

    objective_id = fields.Many2one(
        'hr.okr.objective', string='Mục tiêu', required=True, ondelete='cascade',
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(string='Key Result', required=True)
    target_value = fields.Float(string='Mục tiêu', default=100)
    current_value = fields.Float(string='Hiện tại')
    unit = fields.Char(string='Đơn vị', default='%')
    progress = fields.Float(
        string='Tiến độ (%)', compute='_compute_progress', store=True,
    )
    state = fields.Selection([
        ('not_started', 'Chưa bắt đầu'),
        ('in_progress', 'Đang thực hiện'),
        ('done', 'Hoàn thành'),
    ], string='Trạng thái', default='not_started')

    @api.depends('current_value', 'target_value')
    def _compute_progress(self):
        for kr in self:
            if kr.target_value:
                kr.progress = min((kr.current_value / kr.target_value) * 100, 100)
            else:
                kr.progress = 0
