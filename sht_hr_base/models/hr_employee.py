import pytz
from dateutil.relativedelta import relativedelta

from odoo import _, models, fields, api
from odoo.exceptions import ValidationError

VALID_TIMEZONES = set(pytz.all_timezones)


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    @api.constrains('tz')
    def _check_timezone(self):
        for emp in self:
            if emp.tz and emp.tz not in VALID_TIMEZONES:
                raise ValidationError(
                    _('Timezone "%s" không hợp lệ. Sử dụng "Asia/Ho_Chi_Minh" cho Việt Nam.') % emp.tz
                )

    identification_number = fields.Char(
        string='Số CCCD/CMND',
        help='CCCD/CMND number',
        related='identification_id',
        readonly=False,
        groups='hr.group_hr_user',
    )
    tax_id = fields.Char(
        string='Mã số thuế',
        help='Mã số thuế cá nhân',
        groups='hr.group_hr_user',
    )
    social_insurance_id = fields.Char(
        string='Số BHXH',
        help='Số sổ BHXH',
        groups='hr.group_hr_user',
    )
    seniority_start_date = fields.Date(
        string='Ngày bắt đầu thâm niên',
        help='Ngày bắt đầu tính thâm niên',
        groups='hr.group_hr_user',
    )
    seniority_years = fields.Float(
        string='Thâm niên (năm)',
        compute='_compute_seniority_years',
        groups='hr.group_hr_user',
    )
    children_under_72m = fields.Integer(
        string='Con dưới 72 tháng',
        help='Số con nhỏ dưới 72 tháng',
        groups='hr.group_hr_user',
    )
    emergency_contact_name = fields.Char(
        string='Emergency Contact Name',
        groups='hr.group_hr_user',
    )
    emergency_contact_phone = fields.Char(
        string='Emergency Contact Phone',
        groups='hr.group_hr_user',
    )
    bank_name = fields.Char(
        string='Tên ngân hàng',
        help='Tên ngân hàng',
        groups='hr.group_hr_user',
    )
    bank_account_number = fields.Char(
        string='Số tài khoản',
        help='Số tài khoản ngân hàng',
        groups='hr.group_hr_user',
    )
    document_ids = fields.One2many(
        'sht.hr.employee.document',
        'employee_id',
        string='Documents',
        groups='hr.group_hr_user',
    )
    document_count = fields.Integer(
        string='Document Count',
        compute='_compute_document_count',
        groups='hr.group_hr_user',
    )

    @api.depends('seniority_start_date')
    def _compute_seniority_years(self):
        today = fields.Date.today()
        for employee in self:
            start = employee.seniority_start_date
            if start:
                delta = relativedelta(today, start)
                employee.seniority_years = (
                    delta.years + delta.months / 12.0 + delta.days / 365.2425
                )
            else:
                employee.seniority_years = 0.0

    @api.depends('document_ids')
    def _compute_document_count(self):
        for employee in self:
            employee.document_count = len(employee.document_ids)

    def action_open_employee_documents(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Documents'),
            'res_model': 'sht.hr.employee.document',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }
