# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _


class HrContract(models.Model):
    _inherit = 'hr.contract'

    sht_contract_type_id = fields.Many2one(
        'sht.hr.contract.type',
        string='Loại hợp đồng VN',
        tracking=True,
    )
    probation_end_date = fields.Date(string='Ngày kết thúc thử việc')
    is_probation = fields.Boolean(
        string='Đang thử việc',
        compute='_compute_is_probation',
        store=True,
    )
    renewal_count = fields.Integer(string='Số lần gia hạn', default=0)
    original_start_date = fields.Date(
        string='Ngày bắt đầu gốc',
        help='Ngày ký hợp đồng đầu tiên với công ty',
    )
    termination_reason = fields.Selection(
        string='Lý do chấm dứt',
        selection=[
            ('resignation', 'Tự nguyện nghỉ việc'),
            ('termination', 'Chấm dứt hợp đồng'),
            ('contract_end', 'Hết hạn hợp đồng'),
            ('retirement', 'Nghỉ hưu'),
            ('other', 'Lý do khác'),
        ],
        tracking=True,
    )
    termination_date = fields.Date(string='Ngày chấm dứt', tracking=True)
    termination_note = fields.Text(string='Ghi chú chấm dứt')
    days_to_expire = fields.Integer(string='Số ngày còn lại', compute='_compute_days_to_expire')
    is_expiring_soon = fields.Boolean(
        string='Sắp hết hạn',
        compute='_compute_is_expiring_soon',
        store=True,
    )

    @api.onchange('sht_contract_type_id')
    def _onchange_sht_contract_type_id(self):
        if (
            self.sht_contract_type_id
            and self.sht_contract_type_id.contract_type_id
        ):
            self.contract_type_id = self.sht_contract_type_id.contract_type_id

    def _sync_contract_type(self):
        """Sync contract_type_id from sht_contract_type_id (for create/write flows)."""
        for rec in self:
            if (
                rec.sht_contract_type_id
                and rec.sht_contract_type_id.contract_type_id
                and rec.contract_type_id != rec.sht_contract_type_id.contract_type_id
            ):
                rec.contract_type_id = rec.sht_contract_type_id.contract_type_id

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_contract_type()
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'sht_contract_type_id' in vals:
            self._sync_contract_type()
        return res

    @api.depends('sht_contract_type_id.code')
    def _compute_is_probation(self):
        for contract in self:
            contract.is_probation = (
                contract.sht_contract_type_id.code == 'PROBATION'
            )

    @api.depends('date_end')
    def _compute_days_to_expire(self):
        today = fields.Date.today()
        for contract in self:
            if contract.date_end:
                contract.days_to_expire = (contract.date_end - today).days
            else:
                contract.days_to_expire = False

    @api.depends('date_end', 'state')
    def _compute_is_expiring_soon(self):
        today = fields.Date.today()
        for contract in self:
            if contract.date_end and contract.state == 'open':
                d = (contract.date_end - today).days
                contract.is_expiring_soon = 0 <= d <= 30
            else:
                contract.is_expiring_soon = False

    @api.model
    def _cron_check_expiring_contracts(self):
        today = fields.Date.today()
        limit = today + relativedelta(days=30)
        open_contracts = self.search([('state', '=', 'open')])
        if open_contracts:
            open_contracts._compute_is_expiring_soon()
        expiring = self.search([
            ('state', '=', 'open'),
            ('date_end', '!=', False),
            ('date_end', '>=', today),
            ('date_end', '<=', limit),
        ])
        activity_type = self.env.ref('mail.mail_activity_data_todo')
        summary = _('Contract expiring within 30 days')
        Activity = self.env['mail.activity']
        group = self.env.ref('hr.group_hr_manager')

        existing_activities = Activity.search([
            ('res_model', '=', 'hr.contract'),
            ('res_id', 'in', expiring.ids),
            ('summary', '=', summary),
        ])
        already_notified = {(a.res_id, a.user_id.id) for a in existing_activities}

        company_managers_cache = {}
        for contract in expiring:
            cid = contract.company_id.id
            if cid not in company_managers_cache:
                company_managers_cache[cid] = self.env['res.users'].search([
                    ('groups_id', 'in', group.id),
                    '|',
                    ('company_ids', 'in', cid),
                    ('company_ids', '=', False),
                ])
            managers = company_managers_cache[cid]
            if not managers:
                continue
            user = (
                contract.hr_responsible_id
                if contract.hr_responsible_id in managers
                else managers[0]
            )
            if (contract.id, user.id) in already_notified:
                continue
            note = _('Contract %s for %s ends on %s.') % (
                contract.name,
                contract.employee_id.name or '',
                contract.date_end,
            )
            Activity.create({
                'res_model': 'hr.contract',
                'res_id': contract.id,
                'activity_type_id': activity_type.id,
                'summary': summary,
                'note': note,
                'date_deadline': today,
                'user_id': user.id,
            })
