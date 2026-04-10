from odoo import fields, models


class HrSignTemplate(models.Model):
    _name = 'hr.sign.template'
    _description = 'Mẫu chữ ký'
    _order = 'name'
    _check_company_auto = True

    name = fields.Char(string='Tên mẫu', required=True)
    job_id = fields.Many2one('hr.job', string='Chức danh')
    user_id = fields.Many2one('res.users', string='Người dùng')
    signature_image = fields.Binary(string='Hình chữ ký')
    is_initial = fields.Boolean(string='Chữ ký nháy', default=False)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', string='Công ty',
        default=lambda self: self.env.company,
    )
