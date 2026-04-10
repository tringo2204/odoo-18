from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ShtHrAppraisalCycle(models.Model):
    _name = 'sht.hr.appraisal.cycle'
    _description = 'Kỳ đánh giá'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_from desc'
    _check_company_auto = True

    name = fields.Char(
        string='Tên kỳ', required=True, tracking=True,
        readonly=True, copy=False, default='Mới',
    )
    date_from = fields.Date(string='Từ ngày', required=True, tracking=True)
    date_to = fields.Date(string='Đến ngày', required=True, tracking=True)
    period_type = fields.Selection([
        ('monthly', 'Hàng tháng'),
        ('quarterly', 'Hàng quý'),
        ('yearly', 'Hàng năm'),
    ], string='Chu kỳ', required=True, default='quarterly', tracking=True)
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('in_progress', 'Đang đánh giá'),
        ('completed', 'Hoàn thành'),
    ], string='Trạng thái', default='draft', tracking=True)
    department_ids = fields.Many2many(
        'hr.department', string='Phòng ban áp dụng',
    )
    template_id = fields.Many2one(
        'sht.hr.appraisal.template', string='Mẫu đánh giá',
    )
    appraisal_ids = fields.One2many(
        'hr.appraisal', 'appraisal_cycle_id', string='Phiếu đánh giá',
    )
    total_count = fields.Integer(
        string='Tổng phiếu', compute='_compute_counts',
    )
    completed_count = fields.Integer(
        string='Đã hoàn thành', compute='_compute_counts',
    )
    pending_count = fields.Integer(
        string='Chờ đánh giá', compute='_compute_counts',
    )
    company_id = fields.Many2one(
        'res.company', string='Công ty',
        default=lambda self: self.env.company,
    )
    note = fields.Text(string='Ghi chú')

    @api.depends('appraisal_ids', 'appraisal_ids.state')
    def _compute_counts(self):
        for rec in self:
            appraisals = rec.appraisal_ids
            rec.total_count = len(appraisals)
            rec.completed_count = len(
                appraisals.filtered(lambda a: a.state == 'done')
            )
            rec.pending_count = rec.total_count - rec.completed_count

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Mới') == 'Mới':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'sht.hr.appraisal.cycle',
                ) or 'Mới'
        return super().create(vals_list)

    def action_start(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Chỉ bắt đầu kỳ đánh giá ở trạng thái Nháp.'))
        self.write({'state': 'in_progress'})

    def action_complete(self):
        for rec in self:
            if rec.state != 'in_progress':
                raise UserError(_('Chỉ hoàn thành kỳ đang đánh giá.'))
        self.write({'state': 'completed'})

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_generate_appraisals(self):
        """Tạo phiếu đánh giá cho NV trong các phòng ban đã chọn."""
        self.ensure_one()
        if self.state != 'in_progress':
            raise UserError(_('Phải bắt đầu kỳ đánh giá trước.'))

        domain = [('company_id', '=', self.company_id.id)]
        if self.department_ids:
            domain.append(('department_id', 'in', self.department_ids.ids))

        employees = self.env['hr.employee'].search(domain)
        existing = self.appraisal_ids.mapped('employee_id')
        new_employees = employees - existing

        Appraisal = self.env['hr.appraisal']
        created = Appraisal
        for emp in new_employees:
            vals = {
                'employee_id': emp.id,
                'appraisal_cycle_id': self.id,
                'date_close': self.date_to,
                'sht_template_id': self.template_id.id if self.template_id else False,
            }
            appraisal = Appraisal.create(vals)
            # Generate lines from template
            if self.template_id:
                appraisal._generate_lines_from_template()
            created |= appraisal

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Tạo phiếu đánh giá'),
                'message': _('Đã tạo %d phiếu đánh giá.') % len(created),
                'type': 'success',
                'sticky': False,
            },
        }

    def action_view_appraisals(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Phiếu đánh giá'),
            'res_model': 'hr.appraisal',
            'view_mode': 'list,form',
            'domain': [('appraisal_cycle_id', '=', self.id)],
        }
