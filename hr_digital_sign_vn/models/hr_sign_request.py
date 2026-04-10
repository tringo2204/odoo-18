from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrSignRequest(models.Model):
    _name = 'hr.sign.request'
    _description = 'Yêu cầu ký số'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _check_company_auto = True

    name = fields.Char(string='Mã yêu cầu', readonly=True, copy=False, default='Mới')
    document_type = fields.Selection([
        ('contract', 'Hợp đồng lao động'),
        ('decision', 'Quyết định'),
        ('appendix', 'Phụ lục'),
        ('other', 'Khác'),
    ], string='Loại tài liệu', required=True, tracking=True)
    employee_id = fields.Many2one(
        'hr.employee', string='Nhân viên liên quan', tracking=True,
    )
    department_id = fields.Many2one(
        'hr.department', string='Phòng ban',
        related='employee_id.department_id', store=True,
    )
    document_file = fields.Binary(string='Tài liệu', required=True)
    document_filename = fields.Char(string='Tên file')
    signed_file = fields.Binary(string='Tài liệu đã ký', readonly=True)
    signed_filename = fields.Char()
    signer_ids = fields.One2many(
        'hr.sign.signer', 'request_id', string='Người ký',
    )
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('sent', 'Đã gửi'),
        ('partially_signed', 'Ký một phần'),
        ('fully_signed', 'Đã ký đủ'),
        ('cancelled', 'Đã hủy'),
    ], string='Trạng thái', default='draft', tracking=True)
    date_sent = fields.Datetime(string='Ngày gửi', readonly=True)
    date_completed = fields.Datetime(string='Ngày hoàn thành', readonly=True)
    company_id = fields.Many2one(
        'res.company', string='Công ty',
        default=lambda self: self.env.company,
    )
    note = fields.Text(string='Ghi chú')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Mới') == 'Mới':
                vals['name'] = self.env['ir.sequence'].next_by_code('hr.sign.request') or 'Mới'
        return super().create(vals_list)

    def action_send(self):
        for rec in self:
            if not rec.signer_ids:
                raise UserError(_('Phải thêm ít nhất 1 người ký.'))
            rec.write({
                'state': 'sent',
                'date_sent': fields.Datetime.now(),
            })
            # Notify first signer
            first = rec.signer_ids.sorted('sequence')[:1]
            if first and first.signer_id:
                rec.activity_schedule(
                    act_type_xmlid='mail.mail_activity_data_todo',
                    summary=_('Ký tài liệu: %s') % rec.name,
                    user_id=first.signer_id.id,
                )

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_draft(self):
        self.filtered(lambda r: r.state == 'cancelled').write({'state': 'draft'})

    def _check_fully_signed(self):
        self.ensure_one()
        pending = self.signer_ids.filtered(lambda s: s.state == 'pending')
        signed = self.signer_ids.filtered(lambda s: s.state == 'signed')
        if not pending and signed:
            self.write({
                'state': 'fully_signed',
                'date_completed': fields.Datetime.now(),
            })
            self.message_post(body=_('Tài liệu đã được ký đầy đủ.'))
        elif signed:
            self.write({'state': 'partially_signed'})


class HrSignSigner(models.Model):
    _name = 'hr.sign.signer'
    _description = 'Người ký'
    _order = 'sequence'

    request_id = fields.Many2one(
        'hr.sign.request', string='Yêu cầu ký', required=True, ondelete='cascade',
    )
    sequence = fields.Integer(string='Thứ tự ký', default=10)
    signer_id = fields.Many2one(
        'res.users', string='Người ký', required=True,
    )
    role = fields.Selection([
        ('employee', 'Nhân viên'),
        ('manager', 'Quản lý'),
        ('hr_director', 'Giám đốc nhân sự'),
        ('legal', 'Pháp lý'),
    ], string='Vai trò', default='employee')
    state = fields.Selection([
        ('pending', 'Chờ ký'),
        ('signed', 'Đã ký'),
        ('refused', 'Từ chối'),
    ], string='Trạng thái', default='pending')
    signed_date = fields.Datetime(string='Ngày ký', readonly=True)
    signature = fields.Binary(string='Chữ ký')
    signature_type = fields.Selection([
        ('draw', 'Vẽ tay'),
        ('upload', 'Upload'),
        ('template', 'Từ mẫu'),
    ], string='Loại chữ ký', default='draw')
    note = fields.Text(string='Ghi chú')

    def action_sign(self):
        for rec in self:
            if rec.state != 'pending':
                raise UserError(_('Chỉ ký khi đang ở trạng thái Chờ ký.'))
            rec.write({
                'state': 'signed',
                'signed_date': fields.Datetime.now(),
            })
            rec.request_id.message_post(
                body=_('%s đã ký tài liệu.') % rec.signer_id.name,
            )
            rec.request_id._check_fully_signed()
            # Notify next signer
            next_signer = rec.request_id.signer_ids.filtered(
                lambda s: s.state == 'pending' and s.sequence > rec.sequence
            ).sorted('sequence')[:1]
            if next_signer and next_signer.signer_id:
                rec.request_id.activity_schedule(
                    act_type_xmlid='mail.mail_activity_data_todo',
                    summary=_('Đến lượt ký: %s') % rec.request_id.name,
                    user_id=next_signer.signer_id.id,
                )

    def action_refuse(self):
        for rec in self:
            rec.write({'state': 'refused'})
            rec.request_id.message_post(
                body=_('%s đã từ chối ký tài liệu. Lý do: %s') % (
                    rec.signer_id.name, rec.note or ''),
            )
