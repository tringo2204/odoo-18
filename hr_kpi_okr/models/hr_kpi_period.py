from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrKpiPeriod(models.Model):
    _name = 'hr.kpi.period'
    _description = 'Kỳ đánh giá KPI'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_from desc'

    name = fields.Char(string='Mã kỳ', readonly=True, copy=False, default='Mới')
    date_from = fields.Date(string='Từ ngày', required=True, tracking=True)
    date_to = fields.Date(string='Đến ngày', required=True, tracking=True)
    period_type = fields.Selection([
        ('monthly', 'Hàng tháng'),
        ('quarterly', 'Hàng quý'),
        ('yearly', 'Hàng năm'),
    ], string='Chu kỳ', required=True, default='quarterly')
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('in_progress', 'Đang đánh giá'),
        ('completed', 'Hoàn thành'),
    ], string='Trạng thái', default='draft', tracking=True)
    template_id = fields.Many2one('hr.kpi.template', string='Mẫu KPI')
    department_ids = fields.Many2many('hr.department', string='Phòng ban')
    assignment_ids = fields.One2many(
        'hr.kpi.assignment', 'period_id', string='Phân công KPI',
    )
    total_count = fields.Integer(compute='_compute_counts')
    completed_count = fields.Integer(compute='_compute_counts')
    company_id = fields.Many2one(
        'res.company', string='Công ty',
        default=lambda self: self.env.company,
    )

    @api.depends('assignment_ids.state')
    def _compute_counts(self):
        for rec in self:
            rec.total_count = len(rec.assignment_ids)
            rec.completed_count = len(
                rec.assignment_ids.filtered(lambda a: a.state == 'done')
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Mới') == 'Mới':
                vals['name'] = self.env['ir.sequence'].next_by_code('hr.kpi.period') or 'Mới'
        return super().create(vals_list)

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_complete(self):
        self.write({'state': 'completed'})

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_generate_assignments(self):
        self.ensure_one()
        if self.state != 'in_progress':
            raise UserError(_('Phải bắt đầu kỳ trước.'))
        domain = [('company_id', '=', self.company_id.id)]
        if self.department_ids:
            domain.append(('department_id', 'in', self.department_ids.ids))
        employees = self.env['hr.employee'].search(domain)
        existing = self.assignment_ids.mapped('employee_id')
        Assignment = self.env['hr.kpi.assignment']
        created = 0
        for emp in employees - existing:
            assignment = Assignment.create({
                'period_id': self.id,
                'employee_id': emp.id,
                'template_id': self.template_id.id if self.template_id else False,
            })
            if self.template_id:
                assignment._generate_lines()
            created += 1
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Tạo KPI'),
                'message': _('Đã tạo %d phân công KPI.') % created,
                'type': 'success',
                'sticky': False,
            },
        }
