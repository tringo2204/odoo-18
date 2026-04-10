import logging
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

    name = fields.Char(string='Số đơn', readonly=True, copy=False, default='Mới')
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
    duration_days = fields.Float(string='Số ngày', compute='_compute_duration', store=True)
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
    shift_to_id = fields.Many2one(
        'planning.slot', string='Ca muốn đổi sang',
        help='Ca muốn nhận (của NV khác)',
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

    # --- SPECIAL_SCHEDULE ---
    special_schedule_type = fields.Selection(
        [('late_arrival', 'Đi muộn'), ('early_departure', 'Về sớm')],
        string='Loại chế độ',
    )

    # --- RESIGNATION ---
    resignation_date = fields.Date(string='Ngày muốn nghỉ việc')
    resignation_reason = fields.Text(string='Lý do nghỉ việc')

    # ==========================================================================
    # LINK FIELDS (auto-populated after approval)
    # ==========================================================================
    leave_id = fields.Many2one('hr.leave', string='Đơn nghỉ phép liên kết', readonly=True)
    attendance_id = fields.Many2one('hr.attendance', string='Chấm công liên kết', readonly=True)
    planning_slot_id = fields.Many2one('planning.slot', string='Ca làm việc liên kết', readonly=True)

    # ==========================================================================
    # COMPUTED
    # ==========================================================================

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

    # ==========================================================================
    # CRUD
    # ==========================================================================

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Mới') == 'Mới':
                vals['name'] = self.env['ir.sequence'].next_by_code('hr.request') or 'Mới'
        return super().create(vals_list)

    # ==========================================================================
    # WORKFLOW ACTIONS
    # ==========================================================================

    def action_submit(self):
        for rec in self:
            rec._check_frequency()
            rec._create_approval_records()
        self.write({'state': 'submitted'})

    def action_approve(self):
        for rec in self:
            pending = rec.approval_ids.filtered(
                lambda a: a.status == 'pending' and a.approver_id == self.env.user
            )
            if not pending:
                raise UserError(_('Bạn không có quyền duyệt đơn này.'))
            pending[0].write({
                'status': 'approved',
                'approved_date': fields.Datetime.now(),
            })
            all_done = all(
                a.status == 'approved' for a in rec.approval_ids if a.status != 'refused'
            )
            if all_done:
                rec.write({'state': 'approved'})
                rec._execute_side_effects()

    def action_refuse(self):
        for rec in self:
            pending = rec.approval_ids.filtered(
                lambda a: a.status == 'pending' and a.approver_id == self.env.user
            )
            if pending:
                pending[0].write({
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
        self.approval_ids.unlink()
        for rule in self.request_type_id.approval_rule_ids.sorted('sequence'):
            approver = self._resolve_approver(rule)
            if approver:
                self.env['hr.request.approval'].create({
                    'request_id': self.id,
                    'approver_id': approver.id,
                    'sequence': rule.sequence,
                    'status': 'pending',
                })

    def _resolve_approver(self, rule):
        if rule.approver_type == 'direct_manager':
            return self.employee_id.parent_id.user_id if self.employee_id.parent_id else False
        elif rule.approver_type == 'department_head':
            dept = self.employee_id.department_id
            return dept.manager_id.user_id if dept and dept.manager_id else False
        elif rule.approver_type == 'hr':
            group = self.env.ref('hr.group_hr_manager', raise_if_not_found=False)
            if group:
                return group.users[:1] if group.users else False
            return False
        elif rule.approver_type == 'specific_user':
            return rule.approver_user_id
        return False

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
            'request_date_from': self.date_from.date() if self.date_from else False,
            'request_date_to': self.date_to.date() if self.date_to else False,
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
        """Tạo hr.leave loại vắng mặt."""
        absence_type = self.env.ref(
            'hr_request_vn.leave_type_absence', raise_if_not_found=False
        ) or self.env['hr.leave.type'].search([
            ('requires_allocation', '=', 'no'),
        ], limit=1)
        if not absence_type:
            return
        leave = self.env['hr.leave'].sudo().with_context(
            tracking_disable=True,
            leave_fast_create=True,
        ).create({
            'employee_id': self.employee_id.id,
            'holiday_status_id': absence_type.id,
            'request_date_from': self.date_from.date() if self.date_from else False,
            'request_date_to': self.date_to.date() if self.date_to else False,
            'notes': self.description or '',
        })
        leave.action_approve()
        self.leave_id = leave.id

    def _side_effect_ot(self):
        """Ghi nhận giờ OT vào chấm công."""
        _logger.info("OT request %s approved for %s: %s hours",
                      self.name, self.employee_id.name, self.ot_hours)

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

    def _side_effect_extra_shift(self):
        """Tạo planning.slot mới cho NV (tăng ca)."""
        if not self.extra_shift_date:
            return
        resource = self.employee_id.resource_id
        if not resource:
            _logger.warning("Employee %s has no resource for shift creation", self.employee_id.name)
            return
        start_dt = datetime.combine(self.extra_shift_date, time(int(self.extra_shift_start), int((self.extra_shift_start % 1) * 60)))
        end_dt = datetime.combine(self.extra_shift_date, time(int(self.extra_shift_end), int((self.extra_shift_end % 1) * 60)))
        slot = self.env['planning.slot'].sudo().create({
            'resource_id': resource.id,
            'start_datetime': start_dt,
            'end_datetime': end_dt,
            'state': 'published',
        })
        self.planning_slot_id = slot.id

    def _side_effect_shift_reg(self):
        """Tạo planning.slot mới (đăng ký ca)."""
        if not self.shift_reg_date:
            return
        resource = self.employee_id.resource_id
        if not resource:
            _logger.warning("Employee %s has no resource for shift creation", self.employee_id.name)
            return
        start_dt = datetime.combine(self.shift_reg_date, time(int(self.shift_reg_start), int((self.shift_reg_start % 1) * 60)))
        end_dt = datetime.combine(self.shift_reg_date, time(int(self.shift_reg_end), int((self.shift_reg_end % 1) * 60)))
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
        leave = self.env['hr.leave'].sudo().with_context(
            tracking_disable=True,
            leave_fast_create=True,
        ).create({
            'employee_id': self.employee_id.id,
            'holiday_status_id': trip_type.id,
            'request_date_from': self.date_from.date() if self.date_from else False,
            'request_date_to': self.date_to.date() if self.date_to else False,
            'notes': f"Công tác tại: {self.business_trip_location or ''}",
        })
        leave.action_approve()
        self.leave_id = leave.id

    def _side_effect_special_schedule(self):
        """Ghi log chế độ đặc biệt (đi muộn/về sớm)."""
        _logger.info("Special schedule %s for %s: %s",
                      self.name, self.employee_id.name, self.special_schedule_type)

    def _side_effect_resignation(self):
        """Set departure_date trên employee."""
        if self.resignation_date:
            self.employee_id.write({
                'departure_date': self.resignation_date,
            })
            _logger.info("Employee %s resignation set for %s",
                          self.employee_id.name, self.resignation_date)
