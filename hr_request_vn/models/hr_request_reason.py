from odoo import fields, models


class HrRequestReason(models.Model):
    _name = 'hr.request.reason'
    _description = 'Lý do đơn từ'
    _order = 'name'

    name = fields.Char(string='Tên lý do', required=True)
    request_type_id = fields.Many2one(
        'hr.request.type',
        string='Loại đơn',
        required=True,
        ondelete='cascade',
    )
    active = fields.Boolean(default=True)
