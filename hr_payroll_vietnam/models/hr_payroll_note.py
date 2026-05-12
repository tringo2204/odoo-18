from odoo import api, models


class HrPayrollNote(models.Model):
    _inherit = 'hr.payroll.note'

    # #Fix Row 203: dashboard note tabs hiển thị tiếng Việt.
    # 'Note' sinh ra từ _create_dashboard_notes (res.company init).
    # 'Untitled' sinh ra từ todo_list.js khi user bấm + tạo note mới.
    # Cả 2 đều hardcoded English nên ta intercept ở model create.
    _NAME_TRANSLATIONS = {
        'Note': 'Ghi chú',
        'Untitled': 'Chưa đặt tên',
    }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            name = vals.get('name')
            if name in self._NAME_TRANSLATIONS:
                vals['name'] = self._NAME_TRANSLATIONS[name]
        return super().create(vals_list)
