# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ShtHrOffboarding(models.Model):
    _name = 'sht.hr.offboarding'
    _description = 'Quy trình thôi việc'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'
    _check_company_auto = True

    name = fields.Char(string='Mã quy trình', readonly=True, copy=False, default='Mới')
    employee_id = fields.Many2one(
        'hr.employee', string='Nhân viên', required=True,
        tracking=True, ondelete='restrict',
    )
    department_id = fields.Many2one(
        'hr.department', string='Phòng ban',
        related='employee_id.department_id', store=True,
    )
    resignation_date = fields.Date(string='Ngày nộp đơn', tracking=True)
    last_working_day = fields.Date(string='Ngày làm việc cuối', tracking=True)
    reason = fields.Text(string='Lý do nghỉ việc')
    state = fields.Selection([
        ('draft', 'Nháp'), ('in_progress', 'Đang xử lý'),
        ('completed', 'Hoàn thành'), ('cancelled', 'Đã hủy'),
    ], string='Trạng thái', default='draft', required=True, tracking=True)
    checklist_id = fields.Many2one('sht.hr.checklist', string='Checklist', readonly=True)
    checklist_progress = fields.Float(related='checklist_id.progress', readonly=True)
    company_id = fields.Many2one(
        'res.company', string='Công ty', required=True,
        default=lambda self: self.env.company,
    )
    note = fields.Html(string='Ghi chú')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Mới') == 'Mới':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'sht.hr.offboarding',
                ) or 'Mới'
        return super().create(vals_list)

    def action_start(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Chỉ bắt đầu quy trình ở trạng thái Nháp.'))
            template = self.env['sht.hr.checklist.template'].find_matching_template(
                'offboarding',
                department_id=rec.employee_id.department_id.id,
                job_id=rec.employee_id.job_id.id,
                company_id=rec.company_id.id,
            )
            checklist = self.env['sht.hr.checklist'].create({
                'employee_id': rec.employee_id.id,
                'checklist_type': 'offboarding',
                'template_id': template.id if template else False,
                'company_id': rec.company_id.id,
            })
            if template:
                checklist.action_generate_lines()
            rec.write({'state': 'in_progress', 'checklist_id': checklist.id})

    def action_complete(self):
        for rec in self:
            if rec.state != 'in_progress':
                raise UserError(_('Chỉ hoàn thành quy trình đang xử lý.'))
            if rec.checklist_id and rec.checklist_id.state == 'in_progress':
                rec.checklist_id.action_mark_done()
            rec.write({'state': 'completed'})

    def action_cancel(self):
        for rec in self:
            if rec.state == 'completed':
                raise UserError(_('Không thể hủy quy trình đã hoàn thành.'))
            if rec.checklist_id and rec.checklist_id.state == 'in_progress':
                rec.checklist_id.action_cancel()
            rec.write({'state': 'cancelled'})

    def action_draft(self):
        self.filtered(lambda r: r.state == 'cancelled').write({'state': 'draft'})

    def action_view_checklist(self):
        self.ensure_one()
        if not self.checklist_id:
            raise UserError(_('Chưa có checklist. Bắt đầu quy trình trước.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Checklist thôi việc'),
            'res_model': 'sht.hr.checklist',
            'view_mode': 'form',
            'res_id': self.checklist_id.id,
        }
