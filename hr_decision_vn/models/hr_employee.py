from markupsafe import Markup

from odoo import api, fields, models, _


DECISION_TYPE_LABELS = {
    'reception': ('Tiếp nhận', 'fa-user-plus', 'success'),
    'appointment': ('Bổ nhiệm', 'fa-star', 'primary'),
    'transfer': ('Điều chuyển', 'fa-exchange', 'info'),
    'salary_adjustment': ('Điều chỉnh lương', 'fa-money', 'warning'),
    'reward': ('Khen thưởng', 'fa-trophy', 'success'),
    'discipline': ('Kỷ luật', 'fa-warning', 'danger'),
    'dismissal': ('Miễn nhiệm', 'fa-user-times', 'secondary'),
    'termination': ('Chấm dứt HĐ', 'fa-times-circle', 'danger'),
}

CONTRACT_STATE_VN = {
    'draft': 'Mới',
    'open': 'Đang chạy',
    'close': 'Hết hạn',
    'cancel': 'Đã hủy',
}


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    decision_ids = fields.One2many(
        'hr.vn.decision', 'employee_id',
        string='Quyết định', groups='hr.group_hr_user',
    )
    decision_count = fields.Integer(
        string='Số quyết định',
        compute='_compute_decision_count',
        groups='hr.group_hr_user',
    )
    work_history_html = fields.Html(
        string='Quá trình làm việc',
        compute='_compute_work_history_html',
        sanitize=False,
        groups='hr.group_hr_user',
    )

    @api.depends('decision_ids')
    def _compute_decision_count(self):
        data = self.env['hr.vn.decision'].read_group(
            [('employee_id', 'in', self.ids), ('state', '!=', 'cancelled')],
            ['employee_id'], ['employee_id'],
        )
        mapped = {d['employee_id'][0]: d['employee_id_count'] for d in data}
        for emp in self:
            emp.decision_count = mapped.get(emp.id, 0)

    @api.depends('decision_ids.state', 'decision_ids.effective_date',
                 'contract_ids.state', 'contract_ids.date_start')
    def _compute_work_history_html(self):
        for emp in self:
            entries = emp._get_work_history_entries()
            emp.work_history_html = emp._render_work_history_table(entries)

    def _get_work_history_entries(self):
        self.ensure_one()
        entries = []

        # Contracts
        contracts = self.env['hr.contract'].search([
            ('employee_id', '=', self.id),
        ], order='date_start asc')
        for ct in contracts:
            state_label = CONTRACT_STATE_VN.get(ct.state, ct.state)
            entries.append({
                'date': ct.date_start,
                'icon': 'fa-file-text-o',
                'badge_color': 'primary' if ct.state == 'open' else 'secondary',
                'type': 'Hợp đồng',
                'title': ct.name or '',
                'details': [
                    ('Chức danh', ct.job_id.name if ct.job_id else ''),
                    ('Phòng ban', ct.department_id.name if ct.department_id else ''),
                    ('Lương', '{:,.0f} VNĐ'.format(ct.wage) if ct.wage else ''),
                    ('Đến ngày', fields.Date.to_string(ct.date_end) if ct.date_end else 'Không thời hạn'),
                    ('Trạng thái', state_label),
                ],
            })

        # Decisions (done only)
        decisions = self.env['hr.vn.decision'].search([
            ('employee_id', '=', self.id),
            ('state', '=', 'done'),
        ], order='effective_date asc')
        for dec in decisions:
            label, icon, color = DECISION_TYPE_LABELS.get(
                dec.decision_type, (dec.decision_type, 'fa-circle', 'secondary'))
            details = []
            if dec.job_id:
                details.append(('Chức danh', dec.job_id.name))
            if dec.department_id:
                details.append(('Phòng ban', dec.department_id.name))
            if dec.decision_type == 'salary_adjustment':
                if dec.old_wage:
                    details.append(('Lương cũ', '{:,.0f} VNĐ'.format(dec.old_wage)))
                if dec.new_wage:
                    details.append(('Lương mới', '{:,.0f} VNĐ'.format(dec.new_wage)))
            entries.append({
                'date': dec.effective_date,
                'icon': icon,
                'badge_color': color,
                'type': label,
                'title': dec.name or '',
                'details': details,
            })

        entries.sort(key=lambda e: e['date'] or fields.Date.today())
        return entries

    @staticmethod
    def _render_work_history_table(entries):
        if not entries:
            return Markup(
                '<div class="text-center text-muted p-4">'
                '<i class="fa fa-history fa-3x mb-2"></i>'
                '<p>Chưa có dữ liệu quá trình làm việc.</p>'
                '</div>'
            )

        html = Markup('<div style="max-width:850px;">')
        for e in entries:
            date_str = fields.Date.to_string(e['date']) if e['date'] else ''
            icon = e.get('icon', 'fa-circle')
            color = e.get('badge_color', 'secondary')
            title = e.get('title', '')
            details = e.get('details', [])

            # Detail rows as table for alignment
            detail_html = Markup('')
            if details:
                detail_html = Markup(
                    '<table class="mt-1 small text-muted" style="border-collapse:collapse;">'
                )
                for label, value in details:
                    if value:
                        detail_html += Markup(
                            '<tr>'
                            '<td style="padding:1px 12px 1px 0;white-space:nowrap;">'
                            '<strong>%s:</strong></td>'
                            '<td style="padding:1px 0;">%s</td>'
                            '</tr>'
                        ) % (label, value)
                detail_html += Markup('</table>')

            html += Markup(
                '<div class="d-flex align-items-start mb-3">'
                '<div class="text-center flex-shrink-0" style="width:120px;">'
                '<div class="text-muted small mb-1">%s</div>'
                '<span class="badge bg-%s" style="min-width:100px;">'
                '<i class="fa %s me-1"></i>%s</span>'
                '</div>'
                '<div class="border-start border-2 border-%s ps-3 flex-grow-1">'
                '<strong>%s</strong>'
                '%s'
                '</div>'
                '</div>'
            ) % (date_str, color, icon, e['type'], color, title, detail_html)

        html += Markup('</div>')
        return html

    def action_open_decisions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Quyết định'),
            'res_model': 'hr.vn.decision',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }
