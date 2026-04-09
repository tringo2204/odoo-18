from odoo import fields, models


class HrRequestType(models.Model):
    _name = 'hr.request.type'
    _description = 'Loại đơn từ'
    _order = 'sequence, id'

    name = fields.Char(string='Tên loại đơn', required=True)
    code = fields.Selection(
        selection=[
            ('LEAVE', 'Đơn xin nghỉ'),
            ('ABSENCE', 'Đơn vắng mặt'),
            ('OT', 'Đơn làm thêm giờ'),
            ('CHECKIN', 'Đơn bổ sung chấm công'),
            ('SHIFT_SWAP', 'Đơn đổi ca'),
            ('EXTRA_SHIFT', 'Đơn tăng ca'),
            ('SHIFT_REG', 'Đơn đăng ký ca'),
            ('BUSINESS_TRIP', 'Đơn công tác'),
            ('SPECIAL_SCHEDULE', 'Đơn làm theo chế độ'),
            ('RESIGNATION', 'Đơn thôi việc'),
        ],
        string='Mã loại đơn',
        required=True,
    )
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    create_deadline_days = fields.Integer(
        string='Hạn tạo đơn (ngày)',
        default=0,
        help='Số ngày trước/sau sự kiện để tạo đơn. 0 = không giới hạn.',
    )
    reason_ids = fields.One2many(
        'hr.request.reason',
        'request_type_id',
        string='Danh mục lý do',
    )
    approval_rule_ids = fields.One2many(
        'hr.request.approval.rule',
        'request_type_id',
        string='Quy tắc phê duyệt',
    )
    allow_proxy_create = fields.Boolean(
        string='Cho phép tạo hộ',
        default=False,
        help='Cho phép quản lý tạo đơn thay nhân viên',
    )
    frequency_limit = fields.Integer(
        string='Giới hạn tần suất (lần/tháng)',
        default=0,
        help='Số đơn tối đa mỗi tháng. 0 = không giới hạn.',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Công ty',
        default=lambda self: self.env.company,
    )
