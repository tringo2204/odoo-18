# -*- coding: utf-8 -*-
"""
#143 — Chấm công đúng ca (Shift validation)
#144 — OT → worked days (overtime computation per attendance record)

Each hr.attendance record gains:
  - shift_status  : 'in_shift' | 'overtime' | 'unscheduled'
  - scheduled_hours : hours that fall within a scheduled shift
  - overtime_hours  : hours that fall OUTSIDE any scheduled shift
"""
import logging
from datetime import date, datetime, timedelta

import pytz

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    shift_status = fields.Selection([
        ('in_shift', 'Đúng ca'),
        ('overtime', 'Ngoài ca / OT'),
        ('unscheduled', 'Không có lịch'),
    ], string='Trạng thái ca', compute='_compute_shift_fields', store=True,
       help='Xác định xem bản ghi chấm công có nằm trong ca làm đã lên lịch không')

    scheduled_hours = fields.Float(
        string='Giờ trong ca', compute='_compute_shift_fields', store=True,
        digits=(16, 2),
        help='Số giờ của bản ghi chấm công trùng với lịch làm việc',
    )
    overtime_hours = fields.Float(
        string='Giờ OT', compute='_compute_shift_fields', store=True,
        digits=(16, 2),
        help='Số giờ của bản ghi chấm công vượt ngoài lịch làm việc',
    )

    # ──────────────────────────────────────────────────────────────────
    # Core computation
    # ──────────────────────────────────────────────────────────────────

    @api.depends('employee_id', 'check_in', 'check_out')
    def _compute_shift_fields(self):
        for rec in self:
            if not rec.check_in or not rec.check_out or not rec.employee_id:
                rec.shift_status = 'unscheduled'
                rec.scheduled_hours = 0.0
                rec.overtime_hours = rec.worked_hours or 0.0
                continue

            calendar = rec.employee_id.resource_calendar_id
            if not calendar:
                rec.shift_status = 'unscheduled'
                rec.scheduled_hours = 0.0
                rec.overtime_hours = rec.worked_hours or 0.0
                continue

            scheduled = rec._overlap_with_calendar(
                calendar, rec.check_in, rec.check_out
            )
            total = rec.worked_hours or 0.0
            ot = max(0.0, total - scheduled)

            rec.scheduled_hours = round(scheduled, 2)
            rec.overtime_hours = round(ot, 2)
            if scheduled <= 0:
                rec.shift_status = 'overtime'
            elif ot > 0:
                rec.shift_status = 'overtime'
            else:
                rec.shift_status = 'in_shift'

    def _overlap_with_calendar(self, calendar, check_in_utc, check_out_utc):
        """Return the total hours that [check_in, check_out] overlaps with
        scheduled work intervals defined in resource.calendar.

        All datetime values in UTC; we convert to the calendar's tz for
        day-of-week matching.
        """
        tz_name = calendar.tz or 'UTC'
        local_tz = pytz.timezone(tz_name)

        ci_local = check_in_utc.astimezone(local_tz)
        co_local = check_out_utc.astimezone(local_tz)

        # Collect all schedule intervals that overlap the attendance window.
        # resource.calendar.attendance stores weekday + hour_from/hour_to.
        total_overlap = 0.0

        # Iterate over each calendar day within the attendance span.
        current_date = ci_local.date()
        end_date = co_local.date()

        while current_date <= end_date:
            weekday = current_date.weekday()  # 0=Mon … 6=Sun

            # Find schedule lines for this weekday
            lines = calendar.attendance_ids.filtered(
                lambda l, wd=weekday: int(l.dayofweek) == wd
            )
            for line in lines:
                # Build shift interval in local time
                shift_start = datetime.combine(
                    current_date,
                    (datetime.min + timedelta(hours=line.hour_from)).time(),
                )
                shift_end = datetime.combine(
                    current_date,
                    (datetime.min + timedelta(hours=line.hour_to)).time(),
                )
                shift_start = local_tz.localize(shift_start)
                shift_end = local_tz.localize(shift_end)

                # Overlap with attendance window
                overlap_start = max(ci_local, shift_start)
                overlap_end = min(co_local, shift_end)
                if overlap_end > overlap_start:
                    total_overlap += (overlap_end - overlap_start).total_seconds() / 3600.0

            current_date += timedelta(days=1)

        return total_overlap
