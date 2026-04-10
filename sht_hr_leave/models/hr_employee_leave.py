# -*- coding: utf-8 -*-
import logging
from datetime import date

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class HrEmployeeLeave(models.Model):
    _inherit = 'hr.employee'

    @api.model_create_multi
    def create(self, vals_list):
        employees = super().create(vals_list)
        for emp in employees:
            emp._auto_create_leave_allocations()
        return employees

    def _auto_create_leave_allocations(self):
        """Auto-create leave allocations for leave types requiring allocation."""
        self.ensure_one()
        LeaveType = self.env['hr.leave.type']
        Allocation = self.env['hr.leave.allocation']

        alloc_types = LeaveType.search([('requires_allocation', '=', 'yes')])
        today = fields.Date.today()
        year_start = date(today.year, 1, 1)
        year_end = date(today.year, 12, 31)

        for lt in alloc_types:
            existing = Allocation.search([
                ('employee_id', '=', self.id),
                ('holiday_status_id', '=', lt.id),
                ('state', '=', 'validate'),
            ], limit=1)
            if existing:
                continue

            # Default 12 days for PTO-like types
            days = 12.0
            try:
                alloc = Allocation.create({
                    'holiday_status_id': lt.id,
                    'employee_id': self.id,
                    'number_of_days': days,
                    'date_from': year_start,
                    'date_to': year_end,
                })
                alloc.action_validate()
                _logger.info("Auto-allocated %s days '%s' for %s",
                             days, lt.name, self.name)
            except Exception as e:
                _logger.warning("Failed to auto-allocate '%s' for %s: %s",
                                lt.name, self.name, e)
