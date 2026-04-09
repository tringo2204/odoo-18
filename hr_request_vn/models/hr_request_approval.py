from odoo import fields, models


class HrRequestApproval(models.Model):
    _name = 'hr.request.approval'
    _description = 'Phê duyệt đơn từ'
    _order = 'sequence'

    request_id = fields.Many2one(
        'hr.request', string='Đơn từ', required=True, ondelete='cascade',
    )
    approver_id = fields.Many2one('res.users', string='Người duyệt', required=True)
    sequence = fields.Integer(string='Thứ tự', default=10)
    status = fields.Selection(
        selection=[
            ('pending', 'Chờ duyệt'),
            ('approved', 'Đã duyệt'),
            ('refused', 'Từ chối'),
        ],
        string='Trạng thái',
        default='pending',
    )
    approved_date = fields.Datetime(string='Ngày duyệt')
    note = fields.Text(string='Ghi chú')
