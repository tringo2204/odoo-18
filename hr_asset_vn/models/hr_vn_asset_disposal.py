# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrVnAssetDisposal(models.Model):
    _name = 'hr.vn.asset.disposal'
    _description = 'Biên bản đề xuất thanh lý tài sản'
    _order = 'date desc, id desc'
    _inherit = ['mail.thread']

    name = fields.Char(
        string='Số biên bản', required=True, copy=False,
        readonly=True, default='Mới',
    )
    asset_id = fields.Many2one(
        'hr.vn.asset', string='Tài sản', required=True,
        ondelete='restrict', tracking=True,
        domain="[('state', '!=', 'disposed')]",
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
    residual_value = fields.Float(
        related='asset_id.residual_value', string='Giá trị còn lại', readonly=True,
    )

    date = fields.Date(
        string='Ngày đề xuất', required=True, default=fields.Date.today, tracking=True,
    )
    disposal_reason = fields.Selection([
        ('obsolete', 'Hết khấu hao / lỗi thời'),
        ('damaged', 'Hư hỏng nặng không sửa được'),
        ('lost', 'Mất mát'),
        ('sold', 'Chuyển nhượng / Bán'),
        ('other', 'Lý do khác'),
    ], string='Lý do thanh lý', required=True, tracking=True)
    disposal_reason_note = fields.Text(string='Mô tả chi tiết')
    proposed_value = fields.Float(string='Giá trị thu hồi dự kiến (VND)')

    proposed_by_id = fields.Many2one(
        'res.users', string='Người đề xuất',
        default=lambda self: self.env.user, required=True,
    )
    approved_by_id = fields.Many2one(
        'res.users', string='Người phê duyệt', tracking=True,
    )
    approved_date = fields.Date(string='Ngày phê duyệt', tracking=True)
    rejection_reason = fields.Text(string='Lý do từ chối')

    state = fields.Selection([
        ('draft', 'Nháp'),
        ('submitted', 'Chờ duyệt'),
        ('approved', 'Đã duyệt'),
        ('rejected', 'Từ chối'),
        ('disposed', 'Đã thanh lý'),
    ], string='Trạng thái', default='draft', tracking=True)

    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Mới') == 'Mới':
                vals['name'] = self.env['ir.sequence'].next_by_code('hr.vn.asset.disposal') or 'Mới'
        return super().create(vals_list)

    def action_submit(self):
        for rec in self:
            if rec.asset_id.state == 'allocated':
                raise UserError(_(
                    'Tài sản "%s" đang được cấp phát cho %s.\n'
                    'Vui lòng thu hồi tài sản trước khi lập biên bản thanh lý.'
                ) % (rec.asset_id.name, rec.asset_id.current_employee_id.name))
            rec.write({'state': 'submitted'})

    def action_approve(self):
        for rec in self:
            rec.write({
                'state': 'approved',
                'approved_by_id': self.env.user.id,
                'approved_date': fields.Date.today(),
            })

    def action_reject(self):
        self.write({'state': 'rejected'})

    def action_confirm_disposal(self):
        """Finalize disposal — mark asset as disposed."""
        for rec in self:
            if rec.state != 'approved':
                raise UserError(_('Chỉ có thể hoàn tất thanh lý khi biên bản đã được phê duyệt.'))
            rec.asset_id.write({
                'state': 'disposed',
                'current_employee_id': False,
                'current_department_id': False,
            })
            rec.write({'state': 'disposed'})

    # Aliases so test scripts / button calls using common names all work
    def action_done(self):
        return self.action_confirm_disposal()

    def action_dispose(self):
        return self.action_confirm_disposal()

    def action_reset_draft(self):
        self.write({'state': 'draft'})
