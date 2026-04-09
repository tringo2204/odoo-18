from odoo import fields, models


class ShtHrDocumentType(models.Model):
    _name = 'sht.hr.document.type'
    _description = 'Employee Document Type'
    _order = 'name'

    name = fields.Char(
        string='Name',
        required=True,
        help='Ví dụ: CCCD, Bằng đại học, Hợp đồng lao động',
    )
    code = fields.Char(string='Code', help='Mã loại giấy tờ (tùy chọn)')
    is_required = fields.Boolean(
        string='Required for Onboarding',
        default=False,
        help='Bắt buộc khi onboarding',
    )
    description = fields.Text(string='Description', help='Mô tả thêm')
