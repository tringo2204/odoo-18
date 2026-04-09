from odoo import fields, models


class HrRequestApprovalRule(models.Model):
    _name = 'hr.request.approval.rule'
    _description = 'Quy tắc phê duyệt đơn từ'
    _order = 'sequence'

    request_type_id = fields.Many2one(
        'hr.request.type',
        string='Loại đơn',
        required=True,
        ondelete='cascade',
    )
    sequence = fields.Integer(string='Thứ tự', default=10)
    approver_type = fields.Selection(
        selection=[
            ('direct_manager', 'Quản lý trực tiếp'),
            ('department_head', 'Trưởng phòng'),
            ('hr', 'Phòng nhân sự'),
            ('specific_user', 'Người cụ thể'),
        ],
        string='Người duyệt',
        required=True,
        default='direct_manager',
    )
    approver_user_id = fields.Many2one(
        'res.users',
        string='Người duyệt cụ thể',
    )
    required = fields.Boolean(string='Bắt buộc', default=True)
