# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrVnAssetMaintenance(models.Model):
    _name = 'hr.vn.asset.maintenance'
    _description = 'Yêu cầu bảo trì tài sản'
    _order = 'date desc, id desc'
    _inherit = ['mail.thread']

    name = fields.Char(
        string='Số YC bảo trì', required=True, copy=False,
        readonly=True, default='Mới',
    )
    asset_id = fields.Many2one(
        'hr.vn.asset', string='Tài sản', required=True,
        ondelete='restrict', tracking=True,
        domain="[('state', 'in', ('available', 'allocated', 'maintenance'))]",
    )
    asset_category_id = fields.Many2one(
        'hr.vn.asset.category', string='Danh mục',
        related='asset_id.category_id', readonly=True,
    )
    asset_state = fields.Selection(
        related='asset_id.state', string='Trạng thái tài sản', readonly=True,
    )
    current_employee_id = fields.Many2one(
        related='asset_id.current_employee_id', string='Đang cấp cho', readonly=True,
    )

    date = fields.Date(
        string='Ngày yêu cầu', required=True, default=fields.Date.today, tracking=True,
    )
    maintenance_type = fields.Selection([
        ('routine', 'Bảo trì định kỳ'),
        ('repair', 'Sửa chữa'),
        ('inspection', 'Kiểm tra'),
        ('upgrade', 'Nâng cấp'),
        ('other', 'Khác'),
    ], string='Loại bảo trì', required=True, tracking=True)
    description = fields.Text(string='Mô tả sự cố / yêu cầu')
    maintenance_note = fields.Text(string='Kết quả bảo trì')

    estimated_cost = fields.Float(string='Chi phí dự kiến (VND)')
    actual_cost = fields.Float(string='Chi phí thực tế (VND)')

    requested_by_id = fields.Many2one(
        'res.users', string='Người yêu cầu',
        default=lambda self: self.env.user, required=True,
    )
    approved_by_id = fields.Many2one(
        'res.users', string='Người phê duyệt', tracking=True,
    )
    approved_date = fields.Date(string='Ngày duyệt', tracking=True)
    rejection_reason = fields.Text(string='Lý do từ chối')

    date_start = fields.Date(string='Ngày bắt đầu bảo trì')
    date_done = fields.Date(string='Ngày hoàn tất bảo trì')

    state = fields.Selection([
        ('draft', 'Nháp'),
        ('submitted', 'Chờ duyệt'),
        ('approved', 'Đã duyệt'),
        ('in_progress', 'Đang bảo trì'),
        ('done', 'Hoàn tất'),
        ('rejected', 'Từ chối'),
        ('cancelled', 'Đã hủy'),
    ], string='Trạng thái', default='draft', tracking=True)

    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Mới') == 'Mới':
                vals['name'] = self.env['ir.sequence'].next_by_code('hr.vn.asset.maintenance') or 'Mới'
        return super().create(vals_list)

    def action_submit(self):
        for rec in self:
            rec.write({'state': 'submitted'})

    def action_approve(self):
        for rec in self:
            rec.write({
                'state': 'approved',
                'approved_by_id': self.env.user.id,
                'approved_date': fields.Date.today(),
            })
            # Put asset into maintenance state if not already
            if rec.asset_id.state != 'maintenance':
                rec.asset_id.write({'state': 'maintenance'})

    def action_reject(self):
        self.write({'state': 'rejected'})

    def action_start(self):
        for rec in self:
            if rec.state != 'approved':
                raise UserError(_('Chỉ có thể bắt đầu bảo trì khi yêu cầu đã được phê duyệt.'))
            rec.write({
                'state': 'in_progress',
                'date_start': fields.Date.today(),
            })

    def action_done(self):
        for rec in self:
            if rec.state not in ('approved', 'in_progress'):
                raise UserError(_('Chỉ có thể hoàn tất bảo trì khi yêu cầu đã được duyệt hoặc đang xử lý.'))
            rec.write({
                'state': 'done',
                'date_done': fields.Date.today(),
            })
            # Return asset to available state
            rec.asset_id.write({'state': 'available'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})
