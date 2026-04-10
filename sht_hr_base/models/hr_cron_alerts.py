import logging
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class HrEmployeeAlerts(models.Model):
    _inherit = 'hr.employee'

    @api.model
    def _cron_negative_leave_alert(self):
        """Alert HR when employees have negative leave balance."""
        LeaveType = self.env['hr.leave.type']
        alloc_types = LeaveType.search([('requires_allocation', '=', 'yes')])
        for lt in alloc_types:
            employees = self.search([('active', '=', True)])
            for emp in employees:
                remaining = lt.with_context(employee_id=emp.id).virtual_remaining_leaves
                if remaining is not None and remaining < 0:
                    emp.activity_schedule(
                        act_type_xmlid='mail.mail_activity_data_warning',
                        summary=_('Phép âm: %s (%.1f ngày)') % (lt.name, remaining),
                        user_id=emp.parent_id.user_id.id or self.env.ref('base.user_admin').id,
                    )
                    _logger.info("Negative leave alert: %s has %.1f days of %s",
                                 emp.name, remaining, lt.name)

    @api.model
    def _cron_attendance_anomaly_alert(self):
        """Alert for employees missing check-out yesterday."""
        yesterday = fields.Date.today() - relativedelta(days=1)
        Attendance = self.env['hr.attendance']
        open_attendances = Attendance.search([
            ('check_out', '=', False),
            ('check_in', '<', fields.Datetime.to_string(
                fields.Datetime.from_string(str(yesterday) + ' 00:00:00')
            )),
        ])
        for att in open_attendances:
            att.employee_id.activity_schedule(
                act_type_xmlid='mail.mail_activity_data_warning',
                summary=_('Chấm công bất thường: chưa check-out ngày %s') % att.check_in.date(),
                user_id=att.employee_id.parent_id.user_id.id or self.env.ref('base.user_admin').id,
            )
        if open_attendances:
            _logger.info("Attendance anomaly: %d open check-ins found", len(open_attendances))
