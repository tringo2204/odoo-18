# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ShtHrRecruitmentCampaign(models.Model):
    _name = 'sht.hr.recruitment.campaign'
    _description = 'Chiến dịch tuyển dụng'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc'

    name = fields.Char(
        string='Tên chiến dịch', required=True, tracking=True,
    )
    request_id = fields.Many2one(
        'sht.hr.recruitment.request', string='Đề xuất tuyển dụng',
        ondelete='set null',
    )
    department_id = fields.Many2one(
        'hr.department', string='Phòng ban', required=True,
    )
    job_id = fields.Many2one(
        'hr.job', string='Chức danh', required=True,
    )
    responsible_id = fields.Many2one(
        'res.users', string='Người phụ trách',
        default=lambda self: self.env.user,
    )
    budget = fields.Float(string='Ngân sách')
    channel = fields.Selection([
        ('website', 'Website tuyển dụng'),
        ('referral', 'Giới thiệu nội bộ'),
        ('agency', 'Đơn vị tuyển dụng'),
        ('social', 'Mạng xã hội'),
        ('other', 'Khác'),
    ], string='Kênh tuyển dụng', default='website')
    date_start = fields.Date(string='Ngày bắt đầu', default=fields.Date.today)
    date_end = fields.Date(string='Ngày kết thúc')
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('active', 'Đang tuyển'),
        ('closed', 'Đã đóng'),
    ], string='Trạng thái', default='draft', tracking=True)
    applicant_ids = fields.One2many(
        'hr.applicant', 'campaign_id', string='Ứng viên',
    )
    applicant_count = fields.Integer(
        compute='_compute_applicant_count', string='Số ứng viên',
    )
    hired_count = fields.Integer(
        compute='_compute_applicant_count', string='Đã tuyển',
    )
    company_id = fields.Many2one(
        'res.company', string='Công ty',
        default=lambda self: self.env.company,
    )
    note = fields.Text(string='Ghi chú')

    @api.depends('applicant_ids', 'applicant_ids.stage_id')
    def _compute_applicant_count(self):
        for rec in self:
            rec.applicant_count = len(rec.applicant_ids)
            rec.hired_count = len(
                rec.applicant_ids.filtered(lambda a: a.stage_id.hired_stage)
            )

    def action_start(self):
        self.write({'state': 'active'})

    def action_close(self):
        self.write({'state': 'closed'})

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_view_applicants(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Ứng viên'),
            'res_model': 'hr.applicant',
            'view_mode': 'list,kanban,form',
            'domain': [('campaign_id', '=', self.id)],
            'context': {
                'default_campaign_id': self.id,
                'default_department_id': self.department_id.id,
                'default_job_id': self.job_id.id,
            },
        }
