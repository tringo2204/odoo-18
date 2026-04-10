# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ShtHrRecruitmentRequest(models.Model):
    _name = 'sht.hr.recruitment.request'
    _description = 'Đề xuất tuyển dụng'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Mã đề xuất', readonly=True, copy=False, default='Mới',
    )
    department_id = fields.Many2one(
        'hr.department', string='Phòng ban', required=True, tracking=True,
    )
    job_id = fields.Many2one(
        'hr.job', string='Chức danh', required=True, tracking=True,
    )
    request_type = fields.Selection([
        ('replacement', 'Thay thế'),
        ('addition', 'Bổ sung'),
        ('planned', 'Theo kế hoạch'),
    ], string='Loại đề xuất', required=True, default='addition', tracking=True)
    quantity = fields.Integer(string='Số lượng', required=True, default=1)
    reason = fields.Text(string='Lý do đề xuất')
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('submitted', 'Đã trình'),
        ('approved', 'Đã duyệt'),
        ('rejected', 'Từ chối'),
    ], string='Trạng thái', default='draft', tracking=True)
    requested_by = fields.Many2one(
        'res.users', string='Người đề xuất',
        default=lambda self: self.env.user, readonly=True,
    )
    approved_by = fields.Many2one(
        'res.users', string='Người duyệt', readonly=True,
    )
    approved_date = fields.Datetime(string='Ngày duyệt', readonly=True)
    campaign_ids = fields.One2many(
        'sht.hr.recruitment.campaign', 'request_id',
        string='Chiến dịch tuyển dụng',
    )
    campaign_count = fields.Integer(
        compute='_compute_campaign_count', string='Số chiến dịch',
    )
    company_id = fields.Many2one(
        'res.company', string='Công ty',
        default=lambda self: self.env.company,
    )

    @api.depends('campaign_ids')
    def _compute_campaign_count(self):
        for rec in self:
            rec.campaign_count = len(rec.campaign_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Mới') == 'Mới':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'sht.hr.recruitment.request',
                ) or 'Mới'
        return super().create(vals_list)

    def action_submit(self):
        self.write({'state': 'submitted'})

    def action_approve(self):
        self.write({
            'state': 'approved',
            'approved_by': self.env.uid,
            'approved_date': fields.Datetime.now(),
        })

    def action_reject(self):
        self.write({'state': 'rejected'})

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_create_campaign(self):
        """Tạo chiến dịch tuyển dụng từ đề xuất đã duyệt."""
        self.ensure_one()
        if self.state != 'approved':
            raise UserError(_('Chỉ tạo chiến dịch từ đề xuất đã duyệt.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Tạo chiến dịch tuyển dụng'),
            'res_model': 'sht.hr.recruitment.campaign',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_request_id': self.id,
                'default_department_id': self.department_id.id,
                'default_job_id': self.job_id.id,
            },
        }

    def action_view_campaigns(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Chiến dịch tuyển dụng'),
            'res_model': 'sht.hr.recruitment.campaign',
            'view_mode': 'list,form',
            'domain': [('request_id', '=', self.id)],
        }
