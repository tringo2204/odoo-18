# -*- coding: utf-8 -*-
"""
#144 — OT giờ từ chấm công → worked days trong bảng lương.
#253 — Phân loại OT theo loại (ngày thường / cuối tuần / lễ / đêm) để
       salary rules tính thành tiền lương trong payslip.

Overrides _get_worked_day_lines() to append one OT worked-day line PER
category, summing overtime_hours from hr.attendance within the pay period
and bucketing each attendance record by:
  - ngày thường  -> OT_WEEKDAY
  - cuối tuần     -> OT_WEEKEND
  - ngày lễ       -> OT_HOLIDAY
  - đêm + cuối tuần -> OT_NIGHT_WEEKEND
  - đêm + ngày lễ   -> OT_NIGHT_HOLIDAY

The matching salary rules live in hr_payroll_vietnam (salary_structure_vn.xml)
and read these lines by work-entry-type code. The override matches the
Odoo 18 enterprise signature exactly.
"""
import logging
from datetime import datetime, time, timedelta

import pytz

from odoo import models

_logger = logging.getLogger(__name__)

# Work-entry-type code per OT bucket (must match codes used by the VN
# salary rules in hr_payroll_vietnam/data/salary_structure_vn.xml).
_OT_TYPES = {
    'weekday': ('OT_WEEKDAY', 'Tăng ca ngày thường'),
    'weekend': ('OT_WEEKEND', 'Tăng ca cuối tuần'),
    'holiday': ('OT_HOLIDAY', 'Tăng ca ngày lễ'),
    'night_weekend': ('OT_NIGHT_WEEKEND', 'Tăng ca đêm cuối tuần'),
    'night_holiday': ('OT_NIGHT_HOLIDAY', 'Tăng ca đêm ngày lễ/tết'),
}

# Night window (giờ địa phương): 22:00 → 06:00.
_NIGHT_START = 22
_NIGHT_END = 6


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    # ──────────────────────────────────────────────────────────────────
    # Worked-day line overrides
    # ──────────────────────────────────────────────────────────────────

    def _compute_worked_days_line_ids(self):
        """After base computation, append categorized OT lines (#253)."""
        super()._compute_worked_days_line_ids()
        for slip in self:
            if not (slip.employee_id and slip.date_from and slip.date_to):
                continue
            existing = set(slip.worked_days_line_ids.mapped('work_entry_type_id.code'))
            cmds = [
                (0, 0, vals)
                for code, vals in slip._vn_extra_worked_day_vals()
                if code not in existing
            ]
            if cmds:
                slip.worked_days_line_ids = cmds

    def _get_worked_day_lines(self, domain=None, check_out_of_contract=True):
        """Extend base worked-day lines with categorized OT lines (#253)."""
        res = super()._get_worked_day_lines(
            domain=domain, check_out_of_contract=check_out_of_contract
        )

        # Only add OT when computing regular (non-credit) lines
        if domain and any('is_credit_time' in str(d) for d in domain):
            return res

        existing = {l.get('work_entry_type_id') for l in res}
        for code, vals in self._vn_extra_worked_day_vals():
            if vals['work_entry_type_id'] in existing:
                continue
            res.append(vals)
        return res

    # ──────────────────────────────────────────────────────────────────
    # OT helpers
    # ──────────────────────────────────────────────────────────────────

    def _vn_extra_worked_day_vals(self):
        """All VN-specific extra worked-day lines: OT buckets (#253) + night shift.

        Returns [(code, worked_day_line_vals), ...]. The night-shift line
        (regular night hours, code NIGHT_SHIFT) drives the night allowance
        salary rule in hr_payroll_vietnam.
        """
        self.ensure_one()
        vals = list(self._vn_ot_worked_day_vals())
        night = self._vn_night_shift_worked_day_val()
        if night:
            vals.append(night)
        return vals

    def _vn_night_shift_worked_day_val(self):
        """Worked-day line for regular (non-OT) hours worked in 22:00–06:00.

        Drives the NIGHT_SHIFT allowance rule. OT hours are excluded here so the
        night premium does not stack on top of the OT_NIGHT_* rules.

        ``number_of_days`` / ``number_of_hours`` are intentionally 0: these
        regular night hours are already part of the base (WORK100) worked-day
        line, so counting them here too would double them in the payslip's
        worked-time totals. This line only surfaces the night-shift entry; the
        30% premium is computed by the NIGHT_SHIFT salary rule, which reads the
        hours independently via ``_compute_night_shift_hours()``.
        """
        self.ensure_one()
        hours = self._compute_night_shift_hours()
        if hours <= 0:
            return None
        we_type = self._vn_ot_work_entry_type('NIGHT_SHIFT', 'Giờ làm ca đêm (22:00–06:00)')
        return ('NIGHT_SHIFT', {
            'sequence': 110,
            'work_entry_type_id': we_type.id,
            'number_of_days': 0.0,
            'number_of_hours': 0.0,
        })

    def _vn_ot_worked_day_vals(self):
        """Return [(code, worked_day_line_vals), ...] for each non-zero OT bucket."""
        self.ensure_one()
        buckets = self._compute_ot_hours_by_category()
        contract = self.contract_id
        hours_per_day = (
            contract.resource_calendar_id.hours_per_day
            if contract and contract.resource_calendar_id
            else 8.0
        ) or 8.0

        vals = []
        sequence = 99
        for key, (code, name) in _OT_TYPES.items():
            hours = buckets.get(key, 0.0)
            if hours <= 0:
                continue
            we_type = self._vn_ot_work_entry_type(code, name)
            vals.append((code, {
                'sequence': sequence,
                'work_entry_type_id': we_type.id,
                'number_of_days': round(hours / hours_per_day, 4),
                'number_of_hours': round(hours, 4),
            }))
            sequence += 1
        return vals

    def _vn_ot_work_entry_type(self, code, name):
        """Find (or create) the hr.work.entry.type for an OT bucket."""
        we_type = self.env['hr.work.entry.type'].search(
            [('code', '=', code)], limit=1
        )
        if not we_type:
            we_type = self.env['hr.work.entry.type'].sudo().create({
                'name': name,
                'code': code,
                'color': 4,
                'is_leave': False,
            })
        return we_type

    def _compute_ot_hours_by_category(self):
        """Sum overtime_hours from hr.attendance in the period, bucketed by type.

        Each attendance record's whole OT block is classified by the day type
        (ngày thường / cuối tuần / ngày lễ) and night window of its check-in.
        Night weekday OT is folded into the weekday bucket (no dedicated rule).
        """
        self.ensure_one()
        buckets = {key: 0.0 for key in _OT_TYPES}
        if not (self.employee_id and self.date_from and self.date_to):
            return buckets

        tz_name = (
            (self.contract_id.resource_calendar_id.tz if self.contract_id else None)
            or self.employee_id.resource_calendar_id.tz
            or self.env.user.tz
            or 'UTC'
        )
        local_tz = pytz.timezone(tz_name)

        dt_from = datetime.combine(self.date_from, time.min)
        dt_to = datetime.combine(self.date_to, time.max.replace(microsecond=0))
        dt_from_utc = local_tz.localize(dt_from).astimezone(pytz.utc).replace(tzinfo=None)
        dt_to_utc = local_tz.localize(dt_to).astimezone(pytz.utc).replace(tzinfo=None)

        attendances = self.env['hr.attendance'].search([
            ('employee_id', '=', self.employee_id.id),
            ('check_in', '>=', dt_from_utc),
            ('check_in', '<=', dt_to_utc),
            ('check_out', '!=', False),
        ])
        if not attendances:
            return buckets

        # Flush computed fields to ensure overtime_hours is up-to-date
        attendances.flush_recordset(['overtime_hours'])
        holiday_dates = self._vn_public_holiday_dates()

        for att in attendances:
            ot = att.overtime_hours or 0.0
            if ot <= 0:
                continue
            ci_local = pytz.utc.localize(att.check_in).astimezone(local_tz)
            day = ci_local.date()
            is_holiday = day in holiday_dates
            is_weekend = day.weekday() >= 5  # Sat=5, Sun=6
            is_night = ci_local.hour >= _NIGHT_START or ci_local.hour < _NIGHT_END

            if is_holiday:
                key = 'night_holiday' if is_night else 'holiday'
            elif is_weekend:
                key = 'night_weekend' if is_night else 'weekend'
            else:
                key = 'weekday'
            buckets[key] += ot

        return buckets

    def _compute_night_shift_hours(self):
        """Sum regular (non-OT) hours worked inside the night window 22:00–06:00.

        For each attendance we take the night-window overlap of the whole shift,
        then subtract the night-window overlap of its OT portion. What remains is
        the regular night work that earns the night-shift allowance — OT night
        hours are paid via the dedicated OT_NIGHT_* rules and are deliberately
        not double-counted.

        OT is located from the employee's resource calendar rather than assumed
        to be the shift tail: hours before the scheduled start (early check-in)
        and after the scheduled end (late check-out) are both treated as OT. The
        old tail-only assumption wrongly stripped legitimate night premium for
        early check-in OT (e.g. arriving 04:00 for an 06:00 day shift).
        """
        self.ensure_one()
        if not (self.employee_id and self.date_from and self.date_to):
            return 0.0

        tz_name = (
            (self.contract_id.resource_calendar_id.tz if self.contract_id else None)
            or self.employee_id.resource_calendar_id.tz
            or self.env.user.tz
            or 'UTC'
        )
        local_tz = pytz.timezone(tz_name)

        dt_from = datetime.combine(self.date_from, time.min)
        dt_to = datetime.combine(self.date_to, time.max.replace(microsecond=0))
        dt_from_utc = local_tz.localize(dt_from).astimezone(pytz.utc).replace(tzinfo=None)
        dt_to_utc = local_tz.localize(dt_to).astimezone(pytz.utc).replace(tzinfo=None)

        attendances = self.env['hr.attendance'].search([
            ('employee_id', '=', self.employee_id.id),
            ('check_in', '>=', dt_from_utc),
            ('check_in', '<=', dt_to_utc),
            ('check_out', '!=', False),
        ])
        if not attendances:
            return 0.0
        attendances.flush_recordset(['overtime_hours'])

        calendar = (
            (self.contract_id.resource_calendar_id if self.contract_id else False)
            or self.employee_id.resource_calendar_id
        )

        total = 0.0
        for att in attendances:
            ci = pytz.utc.localize(att.check_in).astimezone(local_tz).replace(tzinfo=None)
            co = pytz.utc.localize(att.check_out).astimezone(local_tz).replace(tzinfo=None)
            night = self._night_overlap_hours(ci, co)
            ot = att.overtime_hours or 0.0
            if ot > 0:
                night -= self._vn_ot_night_overlap(calendar, ci, co, ot)
            total += max(night, 0.0)
        return total

    def _vn_ot_night_overlap(self, calendar, ci, co, ot):
        """Night-window hours that fall inside the OT (out-of-schedule) portion
        of the attendance ``[ci, co]`` (naive local datetimes).

        OT is located from the resource calendar: the part of the shift before
        the scheduled start (prefix / early check-in) and after the scheduled
        end (suffix / late check-out). Their night overlaps are summed so the
        night premium is removed from the correct end(s) of the shift instead of
        blindly from the tail.

        Fallbacks:
          - no usable calendar (or a two-week calendar we don't unpack): keep
            the legacy tail clamp ``[co - ot, co]``;
          - calendar with no scheduled line on the relevant day(s): the whole
            shift is OT, so every night hour is OT night.
        """
        if not calendar or calendar.two_weeks_calendar:
            return self._night_overlap_hours(co - timedelta(hours=ot), co)

        start_bounds = self._vn_day_schedule_bounds(calendar, ci.date())
        if ci.date() != co.date():
            # Cross-midnight shift: use the check-in day's schedule for both
            # bounds. Fetching end_bounds from co.date() (the next day) puts
            # sched_end far in the future, collapsing suffix to 0 and leaving
            # the OT night hours wrongly inside the night premium (double pay).
            end_bounds = start_bounds
        else:
            end_bounds = self._vn_day_schedule_bounds(calendar, co.date())
        if not start_bounds and not end_bounds:
            return self._night_overlap_hours(ci, co)

        sched_start = (start_bounds or end_bounds)[0]
        sched_end = (end_bounds or start_bounds)[1]
        prefix = self._night_overlap_hours(ci, min(co, sched_start))
        suffix = self._night_overlap_hours(max(ci, sched_end), co)
        # Clamp to the actual OT so schedule-geometry divergence from
        # overtime_hours can never over-subtract from the night premium.
        return min(prefix + suffix, ot)

    @staticmethod
    def _vn_day_schedule_bounds(calendar, day):
        """First scheduled start / last scheduled end (naive local datetimes)
        for ``day`` on ``calendar``, or None when the day has no scheduled work.

        Odoo's ``dayofweek`` ('0'=Monday) matches ``date.weekday()``.
        """
        dow = str(day.weekday())
        lines = calendar.attendance_ids.filtered(
            lambda a: a.dayofweek == dow and not a.display_type
        )
        if not lines:
            return None
        base = datetime.combine(day, time.min)
        return (
            base + timedelta(hours=min(lines.mapped('hour_from'))),
            base + timedelta(hours=max(lines.mapped('hour_to'))),
        )

    @staticmethod
    def _night_overlap_hours(start, end):
        """Hours of the [start, end] interval (naive local datetimes) that fall
        within the nightly window 22:00 → 06:00."""
        if end <= start:
            return 0.0
        total = 0.0
        day = start.date() - timedelta(days=1)
        last = end.date()
        while day <= last:
            win_start = datetime.combine(day, time(_NIGHT_START, 0))
            win_end = datetime.combine(day + timedelta(days=1), time(_NIGHT_END, 0))
            lo = max(start, win_start)
            hi = min(end, win_end)
            if hi > lo:
                total += (hi - lo).total_seconds() / 3600.0
            day += timedelta(days=1)
        return total

    def _vn_public_holiday_dates(self):
        """Return a set of date() that fall on a VN public holiday in the period.

        Public holidays are stored as global resource.calendar.leaves
        (resource_id = False), e.g. data/vn_public_holidays.xml.
        """
        self.ensure_one()
        period_from = datetime.combine(self.date_from, time.min)
        period_to = datetime.combine(self.date_to, time.max.replace(microsecond=0))
        leaves = self.env['resource.calendar.leaves'].sudo().search([
            ('resource_id', '=', False),
            ('date_from', '<=', period_to),
            ('date_to', '>=', period_from),
        ])
        dates = set()
        for leave in leaves:
            cur = leave.date_from.date()
            end = leave.date_to.date()
            while cur <= end:
                dates.add(cur)
                cur += timedelta(days=1)
        return dates
