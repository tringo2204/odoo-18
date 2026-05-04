import logging
import pytz
from datetime import datetime, time, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


HOURS_PER_DAY = 8


class HrRequest(models.Model):
    _name = 'hr.request'
    _description = 'Đơn từ'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'
    _check_company_auto = True

    name = fields.Char(string='Số đơn', copy=False, default='Mới')
    employee_id = fields.Many2one(
        'hr.employee', string='Nhân viên', required=True, tracking=True,
        default=lambda self: self.env.user.employee_id,
        ondelete='restrict', index=True,
    )
    request_type_id = fields.Many2one(
        'hr.request.type', string='Loại đơn', required=True, tracking=True,
        ondelete='restrict',
    )
    request_type_code = fields.Selection(related='request_type_id.code', store=True)
    reason_id = fields.Many2one(
        'hr.request.reason', string='Lý do',
        domain="[('request_type_id', '=', request_type_id)]",
    )
    created_by_id = fields.Many2one(
        'res.users', string='Người tạo', default=lambda self: self.env.user, readonly=True,
    )
    date_from = fields.Datetime(string='Từ ngày')
    date_to = fields.Datetime(string='Đến ngày')
    duration_hours = fields.Float(string='Số giờ', compute='_compute_duration', store=True)
    duration_days = fields.Float(string='Số ngày', compute='_compute_duration', store=True, digits=(16, 0))
    description = fields.Text(string='Mô tả / Ghi chú')
    state = fields.Selection(
        selection=[
            ('draft', 'Nháp'),
            ('submitted', 'Đã nộp'),
            ('approved', 'Đã duyệt'),
            ('refused', 'Từ chối'),
            ('cancelled', 'Đã hủy'),
        ],
        string='Trạng thái', default='draft', tracking=True,
    )
    approval_ids = fields.One2many('hr.request.approval', 'request_id', string='Lịch sử phê duyệt')
    company_id = fields.Many2one(
        'res.company', string='Công ty', default=lambda self: self.env.company,
        index=True,
    )

    # ==========================================================================
    # TYPE-SPECIFIC FIELDS
    # ==========================================================================

    # --- LEAVE ---
    leave_type_id = fields.Many2one(
        'hr.leave.type', string='Loại nghỉ phép',
        help='Chọn loại nghỉ phép (phép năm, nghỉ bù, nghỉ không lương...)',
    )
    request_unit_half = fields.Boolean(string='Nghỉ nửa ngày')
    request_date_from_period = fields.Selection(
        [('am', 'Sáng'), ('pm', 'Chiều')],
        string='Buổi',
    )

    # --- ABSENCE (hour-based) ---
    absence_date = fields.Date(string='Ngày vắng mặt')
    request_hour_from = fields.Float(string='Giờ bắt đầu', digits=(2, 2))
    request_hour_to = fields.Float(string='Giờ kết thúc', digits=(2, 2))

    # --- OT ---
    ot_hours = fields.Float(string='Số giờ OT')

    # --- CHECKIN ---
    checkin_type = fields.Selection(
        [('check_in', 'Check-in'), ('check_out', 'Check-out')],
        string='Loại chấm công',
    )
    checkin_time = fields.Datetime(string='Giờ chấm công bổ sung')

    # --- SHIFT_SWAP ---
    shift_from_id = fields.Many2one(
        'planning.slot', string='Ca hiện tại',
        help='Ca làm việc hiện tại muốn đổi',
    )
    shift_from_start = fields.Datetime(
        related='shift_from_id.start_datetime', string='Giờ bắt đầu (Ca hiện tại)',
    )
    shift_from_end = fields.Datetime(
        related='shift_from_id.end_datetime', string='Giờ kết thúc (Ca hiện tại)',
    )
    shift_to_id = fields.Many2one(
        'planning.slot', string='Ca muốn đổi sang',
        help='Ca muốn nhận (của NV khác)',
    )
    shift_to_start = fields.Datetime(
        related='shift_to_id.start_datetime', string='Giờ bắt đầu (Ca đổi sang)',
    )
    shift_to_end = fields.Datetime(
        related='shift_to_id.end_datetime', string='Giờ kết thúc (Ca đổi sang)',
    )
    swap_employee_id = fields.Many2one(
        'hr.employee', string='Đổi ca với NV',
        help='Nhân viên đổi ca cùng',
    )

    # --- EXTRA_SHIFT ---
    extra_shift_date = fields.Date(string='Ngày tăng ca')
    extra_shift_start = fields.Float(string='Giờ bắt đầu')
    extra_shift_end = fields.Float(string='Giờ kết thúc')

    # --- SHIFT_REG ---
    shift_reg_date = fields.Date(string='Ngày đăng ký')
    shift_reg_start = fields.Float(string='Giờ bắt đầu')
    shift_reg_end = fields.Float(string='Giờ kết thúc')

    # --- BUSINESS_TRIP ---
    business_trip_location = fields.Char(string='Địa điểm công tác')

    # --- SPECIAL_SCHEDULE (#81) ---
    special_schedule_type = fields.Selection(
        [('late_arrival', 'Đi muộn'), ('early_departure', 'Về sớm')],
        string='Loại chế độ',
    )
    late_minutes = fields.Float(string='Số phút đi muộn', digits=(6, 0))
    early_minutes = fields.Float(string='Số phút về sớm', digits=(6, 0))

    # --- RESIGNATION ---
    resignation_date = fields.Date(string='Ngày nghỉ', required=True, default=lambda self: fields.Date.today())
    resignation_last_working_date = fields.Date(string='Ngày làm việc cuối')
    resignation_announcement_date = fields.Date(string='Ngày công bố quyết định')

    # ==========================================================================
    # LINK FIELDS (auto-populated after approval)
    # ==========================================================================
    leave_id = fields.Many2one('hr.leave', string='Đơn nghỉ phép liên kết', readonly=True)
    attendance_id = fields.Many2one('hr.attendance', string='Chấm công liên kết', readonly=True)
    planning_slot_id = fields.Many2one('planning.slot', string='Ca làm việc liên kết', readonly=True)

    # #88: show expected approval chain in draft
    approval_rule_ids = fields.One2many(
        related='request_type_id.approval_rule_ids',
        string='Quy tắc phê duyệt',
        readonly=True,
    )

    # ==========================================================================
    # COMPUTED
    # ==========================================================================

    @api.onchange('date_from', 'date_to', 'request_type_code')
    def _onchange_check_public_holidays(self):
        """#86: Warn when selected leave dates overlap with company public holidays."""
        if self.request_type_code != 'LEAVE':
            return
        if not self.date_from or not self.date_to:
            return
        company = (
            self.employee_id.company_id
            or self.company_id
            or self.env.company
        )
        calendar = company.resource_calendar_id
        # Search global leaves (resource_id=False) matching the company calendar
        # or without a specific calendar (country-level holidays)
        domain = [
            ('date_from', '<=', self.date_to),
            ('date_to', '>=', self.date_from),
            ('resource_id', '=', False),
            '|',
            ('calendar_id', '=', False),
            ('calendar_id', '=', calendar.id if calendar else False),
        ]
        holidays = self.env['resource.calendar.leaves'].sudo().search(domain)
        if holidays:
            names = ', '.join(
                filter(None, holidays.mapped('name'))
            ) or _('Ngày lễ')
            return {
                'warning': {
                    'title': _('Trùng ngày lễ'),
                    'message': _(
                        'Khoảng thời gian bạn chọn trùng với ngày lễ/nghỉ bù: %s.\n'
                        'Vui lòng kiểm tra lại trước khi nộp đơn.'
                    ) % names,
                }
            }

    @api.depends('date_from', 'date_to')
    def _compute_duration(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_to > rec.date_from:
                delta = rec.date_to - rec.date_from
                rec.duration_hours = delta.total_seconds() / 3600.0
                rec.duration_days = delta.total_seconds() / (3600.0 * HOURS_PER_DAY)
            else:
                rec.duration_hours = 0.0
                rec.duration_days = 0.0

    @api.depends('date_from', 'date_to', 'request_type_code')
    def _compute_calendar_days(self):
        """#80: Business trip day count = inclusive calendar days."""
        for rec in self:
            if rec.date_from and rec.date_to:
                tz_name = rec.employee_id.tz or self.env.user.tz or 'UTC'
                local_tz = pytz.timezone(tz_name)
                d_from = rec.date_from.astimezone(local_tz).date()
                d_to = rec.date_to.astimezone(local_tz).date()
                rec.duration_calendar_days = max((d_to - d_from).days + 1, 1)
            else:
                rec.duration_calendar_days = 0

    duration_calendar_days = fields.Integer(
        string='Số ngày', compute='_compute_calendar_days', store=True,
    )

    # ==========================================================================
    # CRUD
    # ==========================================================================

    @api.model_create_multi
    def create(self, vals_list):
        today = fields.Date.today()
        for vals in vals_list:
            if vals.get('name', 'Mới') == 'Mới':
                vals['name'] = self.env['ir.sequence'].next_by_code('hr.request') or 'Mới'
            # Row 71: ensure resignation_date is never False (required=True at model level)
            if not vals.get('resignation_date'):
                vals['resignation_date'] = today
        return super().create(vals_list)

    # Fields the workflow engine / side-effects may write after submission.
    # Everything else is blocked once state != 'draft'.
    _WRITE_WHITELIST = frozenset({
        'state',
        # linked records set by side-effects after approval
        'leave_id',
        'attendance_id',
        'planning_slot_id',
    })

    def write(self, vals):
        user_fields = set(vals.keys()) - self._WRITE_WHITELIST
        if user_fields:
            locked = self.filtered(lambda r: r.state != 'draft')
            if locked:
                raise UserError(_(
                    'Đơn đã được nộp và không thể chỉnh sửa. '
                    'Vui lòng hủy đơn trước nếu cần thay đổi thông tin.'
                ))
        return super().write(vals)

    # ==========================================================================
    # WORKFLOW ACTIONS
    # ==========================================================================

    def action_submit(self):
        for rec in self:
            rec._check_frequency()
            rec._create_approval_records()
        self.write({'state': 'submitted'})

    def action_open_approve_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Phê duyệt đơn'),
            'res_model': 'hr.request.action.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_request_id': self.id,
                'default_action_type': 'approve',
            },
        }

    def action_open_refuse_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Từ chối đơn'),
            'res_model': 'hr.request.action.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_request_id': self.id,
                'default_action_type': 'refuse',
            },
        }

    def action_approve(self):
        for rec in self:
            all_pending = rec.approval_ids.sudo().filtered(lambda a: a.status == 'pending')
            if not all_pending:
                raise UserError(_('Không còn bước phê duyệt nào đang chờ.'))

            # #87: strict sequential — only the lowest-sequence pending step is active
            min_seq = min(all_pending.mapped('sequence'))
            current_step = all_pending.filtered(lambda a: a.sequence == min_seq)
            my_step = current_step.filtered(lambda a: a.approver_id == self.env.user)
            if not my_step:
                raise UserError(_(
                    'Bạn không có quyền duyệt ở bước này. '
                    'Vui lòng chờ bước trước hoàn thành.'
                ))
            my_step.sudo().write({
                'status': 'approved',
                'approved_date': fields.Datetime.now(),
            })
            all_done = all(
                a.status == 'approved'
                for a in rec.approval_ids.sudo()
            )
            if all_done:
                rec.write({'state': 'approved'})
                rec._execute_side_effects()

    def action_refuse(self):
        for rec in self:
            pending = rec.approval_ids.sudo().filtered(
                lambda a: a.status == 'pending' and a.approver_id == self.env.user
            )
            if pending:
                pending[0].sudo().write({
                    'status': 'refused',
                    'approved_date': fields.Datetime.now(),
                })
        self.write({'state': 'refused'})

    def action_cancel(self):
        if any(r.state in ('approved',) for r in self):
            raise UserError(_('Không thể hủy đơn đã duyệt.'))
        self.write({'state': 'cancelled'})

    def action_draft(self):
        self.write({'state': 'draft'})
        self.approval_ids.unlink()

    # ==========================================================================
    # VALIDATION
    # ==========================================================================

    def _check_frequency(self):
        self.ensure_one()
        limit = self.request_type_id.frequency_limit
        if limit <= 0:
            return
        start_of_month = self.create_date.replace(day=1, hour=0, minute=0, second=0)
        count = self.search_count([
            ('employee_id', '=', self.employee_id.id),
            ('request_type_id', '=', self.request_type_id.id),
            ('state', 'not in', ['cancelled']),
            ('create_date', '>=', start_of_month),
            ('id', '!=', self.id),
        ])
        if count >= limit:
            raise ValidationError(_(
                'Bạn đã vượt quá giới hạn %d đơn/tháng cho loại đơn "%s".',
                limit, self.request_type_id.name,
            ))

    def _create_approval_records(self):
        self.ensure_one()
        # #89: use sudo so regular employees can submit without needing
        # direct write/create access on hr.request.approval
        self.approval_ids.sudo().unlink()
        for rule in self.request_type_id.approval_rule_ids.sorted('sequence'):
            approver = self._resolve_approver(rule)
            if approver:
                self.env['hr.request.approval'].sudo().create({
                    'request_id': self.id,
                    'approver_id': approver.id,
                    'sequence': rule.sequence,
                    'status': 'pending',
                })

    def _resolve_approver(self, rule):
        if rule.approver_type == 'direct_manager':
            # Primary: direct manager's user account
            if self.employee_id.parent_id and self.employee_id.parent_id.user_id:
                return self.employee_id.parent_id.user_id
            # Fallback 1: department head
            dept = self.employee_id.department_id
            if dept and dept.manager_id and dept.manager_id.user_id:
                return dept.manager_id.user_id
            # Fallback 2: first HR manager
            return self._get_hr_manager_user()
        elif rule.approver_type == 'department_head':
            dept = self.employee_id.department_id
            if dept and dept.manager_id and dept.manager_id.user_id:
                return dept.manager_id.user_id
            return self._get_hr_manager_user()
        elif rule.approver_type == 'hr':
            return self._get_hr_manager_user()
        elif rule.approver_type == 'specific_user':
            return rule.approver_user_id
        return False

    def _get_hr_manager_user(self):
        group = self.env.ref('hr.group_hr_manager', raise_if_not_found=False)
        if group and group.users:
            return group.users[:1]
        return self.env.user

    # ==========================================================================
    # SIDE-EFFECTS — auto-execute after all approvals done
    # ==========================================================================

    def _execute_side_effects(self):
        """Dispatch to type-specific side-effect method."""
        self.ensure_one()
        code = (self.request_type_code or '').lower()
        method = f'_side_effect_{code}'
        if hasattr(self, method):
            getattr(self, method)()
        else:
            _logger.info("No side-effect defined for request type %s", self.request_type_code)

    def _side_effect_leave(self):
        """Tạo hr.leave và auto-approve."""
        if not self.leave_type_id:
            return
        vals = {
            'employee_id': self.employee_id.id,
            'holiday_status_id': self.leave_type_id.id,
            'request_date_from': self._utc_to_local_date(self.date_from),
            'request_date_to': self._utc_to_local_date(self.date_to),
            'notes': self.description or '',
        }
        if self.request_unit_half:
            vals['request_unit_half'] = True
            vals['request_date_from_period'] = self.request_date_from_period or 'am'

        leave = self.env['hr.leave'].sudo().with_context(
            tracking_disable=True,
            leave_fast_create=True,
        ).create(vals)
        leave.action_approve()
        self.leave_id = leave.id

    def _side_effect_absence(self):
        """Tạo hr.leave + hr.attendance cho vắng mặt theo giờ (#64)."""
        absence_type = self.env.ref(
            'hr_request_vn.leave_type_absence', raise_if_not_found=False
        ) or self.env['hr.leave.type'].search([
            ('requires_allocation', '=', 'no'),
            ('request_unit', '=', 'hour'),
        ], limit=1)
        if not absence_type:
            return
        # #91: prefer explicit absence_date, fall back to local date from UTC date_from
        absence_date = self.absence_date or self._utc_to_local_date(self.date_from)
        leave_vals = {
            'employee_id': self.employee_id.id,
            'holiday_status_id': absence_type.id,
            'request_date_from': absence_date,
            'request_date_to': absence_date,
            'notes': self.description or '',
        }
        if absence_date and self.request_hour_from and self.request_hour_to:
            # #64: pass hour fields so Odoo computes number_of_hours correctly
            leave_vals.update({
                'request_hour_from': self.request_hour_from,
                'request_hour_to': self.request_hour_to,
            })
        # #64: don't use leave_fast_create — it bypasses hour/day computation
        leave = self.env['hr.leave'].sudo().with_context(
            tracking_disable=True,
        ).create(leave_vals)
        leave.action_approve()
        self.leave_id = leave.id

        # #64: also create hr.attendance to populate attendance_id in linked tab
        if absence_date and self.request_hour_from and self.request_hour_to:
            def _flt_to_time(flt):
                h = int(flt)
                m = int(round((flt - h) * 60))
                return time(h, m)

            ci_local = datetime.combine(absence_date, _flt_to_time(self.request_hour_from))
            co_local = datetime.combine(absence_date, _flt_to_time(self.request_hour_to))
            attendance = self.env['hr.attendance'].sudo().create({
                'employee_id': self.employee_id.id,
                'check_in': self._local_to_utc(ci_local),
                'check_out': self._local_to_utc(co_local),
            })
            self.attendance_id = attendance.id

    def _side_effect_ot(self):
        """Tạo hr.attendance record cho giờ OT."""
        emp = self.employee_id
        if not self.date_from or not self.date_to:
            _logger.info("OT request %s: no dates, skip attendance", self.name)
            return
        # Create attendance record for OT hours
        att = self.env['hr.attendance'].sudo().create({
            'employee_id': emp.id,
            'check_in': self.date_from,
            'check_out': self.date_to,
        })
        self.attendance_id = att.id
        _logger.info("OT attendance created for %s: %s → %s",
                      emp.name, self.date_from, self.date_to)

    def _side_effect_checkin(self):
        """Tạo/cập nhật hr.attendance record."""
        emp = self.employee_id
        if self.checkin_type == 'check_in':
            attendance = self.env['hr.attendance'].create({
                'employee_id': emp.id,
                'check_in': self.checkin_time,
                'in_mode': 'manual',
            })
            self.attendance_id = attendance.id
        elif self.checkin_type == 'check_out':
            # Tìm attendance mở (chưa check_out) gần nhất
            open_att = self.env['hr.attendance'].search([
                ('employee_id', '=', emp.id),
                ('check_out', '=', False),
            ], order='check_in desc', limit=1)
            if open_att:
                open_att.write({
                    'check_out': self.checkin_time,
                    'out_mode': 'manual',
                })
                self.attendance_id = open_att.id

    def _side_effect_shift_swap(self):
        """Swap planning.slot giữa 2 nhân viên."""
        slot_from = self.shift_from_id
        slot_to = self.shift_to_id
        if not slot_from or not slot_to:
            return

        # Swap resource_id
        res_from = slot_from.resource_id
        res_to = slot_to.resource_id
        slot_from.write({'resource_id': res_to.id})
        slot_to.write({'resource_id': res_from.id})
        _logger.info("Shift swap: %s <-> %s", slot_from.display_name, slot_to.display_name)

    def _local_to_utc(self, naive_dt):
        """Convert naive datetime from employee's timezone to UTC."""
        tz_name = self.employee_id.tz or self.env.user.tz or 'UTC'
        local_tz = pytz.timezone(tz_name)
        local_dt = local_tz.localize(naive_dt)
        return local_dt.astimezone(pytz.utc).replace(tzinfo=None)

    def _utc_to_local_date(self, utc_dt):
        """#91/#97: Convert UTC-aware/naive datetime to local date."""
        if not utc_dt:
            return False
        tz_name = self.employee_id.tz or self.env.user.tz or 'UTC'
        local_tz = pytz.timezone(tz_name)
        if utc_dt.tzinfo is None:
            utc_dt = pytz.utc.localize(utc_dt)
        return utc_dt.astimezone(local_tz).date()

    def _side_effect_extra_shift(self):
        """Tạo planning.slot mới cho NV (tăng ca) — lưu UTC."""
        if not self.extra_shift_date:
            return
        resource = self.employee_id.resource_id
        if not resource:
            _logger.warning("Employee %s has no resource for shift creation", self.employee_id.name)
            return
        h_start = int(self.extra_shift_start)
        m_start = int((self.extra_shift_start % 1) * 60)
        h_end = int(self.extra_shift_end)
        m_end = int((self.extra_shift_end % 1) * 60)
        local_start = datetime.combine(self.extra_shift_date, time(h_start, m_start))
        local_end = datetime.combine(self.extra_shift_date, time(h_end, m_end))
        start_dt = self._local_to_utc(local_start)
        end_dt = self._local_to_utc(local_end)
        slot = self.env['planning.slot'].sudo().create({
            'resource_id': resource.id,
            'start_datetime': start_dt,
            'end_datetime': end_dt,
            'state': 'published',
        })
        self.planning_slot_id = slot.id

    def _side_effect_shift_reg(self):
        """Tạo planning.slot mới (đăng ký ca) — lưu UTC."""
        if not self.shift_reg_date:
            return
        resource = self.employee_id.resource_id
        if not resource:
            _logger.warning("Employee %s has no resource for shift creation", self.employee_id.name)
            return
        h_start = int(self.shift_reg_start)
        m_start = int((self.shift_reg_start % 1) * 60)
        h_end = int(self.shift_reg_end)
        m_end = int((self.shift_reg_end % 1) * 60)
        local_start = datetime.combine(self.shift_reg_date, time(h_start, m_start))
        local_end = datetime.combine(self.shift_reg_date, time(h_end, m_end))
        start_dt = self._local_to_utc(local_start)
        end_dt = self._local_to_utc(local_end)
        slot = self.env['planning.slot'].sudo().create({
            'resource_id': resource.id,
            'start_datetime': start_dt,
            'end_datetime': end_dt,
            'state': 'draft',
        })
        self.planning_slot_id = slot.id

    def _side_effect_business_trip(self):
        """Tạo hr.leave loại công tác."""
        trip_type = self.env.ref(
            'hr_request_vn.leave_type_business_trip', raise_if_not_found=False
        ) or self.env['hr.leave.type'].search([
            ('requires_allocation', '=', 'no'),
        ], limit=1)
        if not trip_type:
            return
        # #97: convert UTC datetimes to local dates using employee timezone
        leave = self.env['hr.leave'].sudo().with_context(
            tracking_disable=True,
            leave_fast_create=True,
        ).create({
            'employee_id': self.employee_id.id,
            'holiday_status_id': trip_type.id,
            'request_date_from': self._utc_to_local_date(self.date_from),
            'request_date_to': self._utc_to_local_date(self.date_to),
            'notes': f"Công tác tại: {self.business_trip_location or ''}",
        })
        leave.action_approve()
        self.leave_id = leave.id

    def _side_effect_special_schedule(self):
        """Tạo hr.leave cho chế độ đặc biệt (đi muộn/về sớm)."""
        if not self.date_from or not self.date_to:
            _logger.info("Special schedule %s: no dates, skip", self.name)
            return
        # Create attendance with adjusted hours
        att = self.env['hr.attendance'].sudo().create({
            'employee_id': self.employee_id.id,
            'check_in': self.date_from,
            'check_out': self.date_to,
        })
        self.attendance_id = att.id
        _logger.info("Special schedule attendance for %s: %s (%s)",
                      self.employee_id.name, self.special_schedule_type,
                      self.name)

    def _side_effect_resignation(self):
        """Full offboarding chain: departure → close contract → SI decrease → offboarding → asset alert."""
        emp = self.employee_id
        effective_date = self.resignation_last_working_date or self.date_from and self.date_from.date()
        if not effective_date:
            return

        # 1. Set departure_date
        emp.write({'departure_date': effective_date})

        # 2. Close current contract
        contract = emp.contract_id
        if contract and contract.state == 'open':
            contract.write({'state': 'close', 'date_end': effective_date})
            _logger.info("Contract %s closed for %s", contract.name, emp.name)

        # 3. Create SI decrease history (soft-depend)
        if 'hr.vn.si.record' in self.env:
            si_record = self.env['hr.vn.si.record'].search([
                ('employee_id', '=', emp.id), ('current_status', '=', 'active'),
            ], limit=1)
            if si_record:
                self.env['hr.vn.si.history'].create({
                    'record_id': si_record.id,
                    'change_type': 'decrease',
                    'effective_date': effective_date,
                    'old_salary': si_record.insurance_salary,
                    'new_salary': 0,
                    'reason': 'Nghỉ việc — %s' % (self.description or ''),
                })
                si_record.write({'current_status': 'closed'})

        # 4. Trigger offboarding (soft-depend)
        if 'sht.hr.offboarding' in self.env:
            existing = self.env['sht.hr.offboarding'].search([
                ('employee_id', '=', emp.id),
                ('state', 'not in', ['completed', 'cancelled']),
            ], limit=1)
            if not existing:
                offboarding = self.env['sht.hr.offboarding'].create({
                    'employee_id': emp.id,
                    'resignation_date': effective_date,
                    'last_working_day': self.resignation_last_working_date or effective_date,
                    'reason': self.description or '',
                })
                offboarding.action_start()
                _logger.info("Offboarding %s created for %s", offboarding.name, emp.name)

        # 5. Alert about unreturned assets (soft-depend)
        if 'hr.vn.asset' in self.env:
            assets = self.env['hr.vn.asset'].search([
                ('current_employee_id', '=', emp.id), ('state', '=', 'allocated'),
            ])
            if assets:
                emp.activity_schedule(
                    act_type_xmlid='mail.mail_activity_data_todo',
                    summary=_('Thu hồi %d tài sản') % len(assets),
                    note=_('NV %s nghỉ việc. Tài sản cần thu hồi: %s') % (
                        emp.name, ', '.join(assets.mapped('name'))),
                    user_id=emp.parent_id.user_id.id or self.env.user.id,
                )

        _logger.info("Full resignation chain completed for %s", emp.name)
