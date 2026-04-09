from odoo import api, fields, models, _


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    si_record_ids = fields.One2many(
        'hr.vn.si.record', 'employee_id', string='Hồ sơ bảo hiểm',
    )
    si_record_count = fields.Integer(
        string='Số hồ sơ BH', compute='_compute_si_record_count',
    )

    @api.depends('si_record_ids')
    def _compute_si_record_count(self):
        for emp in self:
            emp.si_record_count = len(emp.si_record_ids)

    def action_open_si_records(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Hồ sơ bảo hiểm'),
            'res_model': 'hr.vn.si.record',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }
