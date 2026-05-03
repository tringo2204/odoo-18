from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrVnSiMonthlyList(models.Model):
    _name = 'hr.vn.si.monthly.list'
    _description = 'Danh sách tăng/giảm BHXH tháng'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'year desc, month desc'
    _check_company_auto = True

    name = fields.Char(
        string='Tên', compute='_compute_name', store=True,
    )
    month = fields.Selection([
        ('1', 'Tháng 1'), ('2', 'Tháng 2'), ('3', 'Tháng 3'),
        ('4', 'Tháng 4'), ('5', 'Tháng 5'), ('6', 'Tháng 6'),
        ('7', 'Tháng 7'), ('8', 'Tháng 8'), ('9', 'Tháng 9'),
        ('10', 'Tháng 10'), ('11', 'Tháng 11'), ('12', 'Tháng 12'),
    ], string='Tháng', required=True, tracking=True)
    year = fields.Integer(
        string='Năm', required=True,
        default=lambda self: fields.Date.today().year,
        tracking=True,
    )
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('confirmed', 'Đã xác nhận'),
        ('exported', 'Đã xuất D02'),
    ], string='Trạng thái', default='draft', tracking=True)
    company_id = fields.Many2one(
        'res.company', string='Công ty',
        default=lambda self: self.env.company,
    )

    # History lines filtered by month/year
    history_ids = fields.One2many(
        'hr.vn.si.history', compute='_compute_history_ids',
        string='Tất cả biến động',
    )
    increase_ids = fields.One2many(
        'hr.vn.si.history', compute='_compute_history_ids',
        string='Danh sách tăng',
    )
    decrease_ids = fields.One2many(
        'hr.vn.si.history', compute='_compute_history_ids',
        string='Danh sách giảm',
    )
    adjust_ids = fields.One2many(
        'hr.vn.si.history', compute='_compute_history_ids',
        string='Danh sách điều chỉnh',
    )
    sick_maternity_ids = fields.One2many(
        'hr.vn.si.history', compute='_compute_history_ids',
        string='Ốm đau / Thai sản',
    )
    total_increase = fields.Integer(
        string='Tổng tăng', compute='_compute_history_ids',
    )
    total_decrease = fields.Integer(
        string='Tổng giảm', compute='_compute_history_ids',
    )
    total_adjust = fields.Integer(
        string='Tổng điều chỉnh', compute='_compute_history_ids',
    )
    total_sick_maternity = fields.Integer(
        string='Tổng ốm đau/thai sản', compute='_compute_history_ids',
    )
    note = fields.Text(string='Ghi chú')

    _sql_constraints = [
        ('month_year_company_uniq',
         'unique(month, year, company_id)',
         'Mỗi tháng chỉ có một danh sách tăng/giảm cho mỗi công ty.'),
    ]

    @api.depends('month', 'year')
    def _compute_name(self):
        for rec in self:
            if rec.month and rec.year:
                rec.name = f'DS tăng/giảm BHXH - T{rec.month}/{rec.year}'
            else:
                rec.name = 'Mới'

    def _get_history_domain(self):
        """Domain cơ sở lấy biến động theo tháng/năm/công ty."""
        self.ensure_one()
        month = int(self.month)
        year = self.year
        date_from = fields.Date.from_string(f'{year}-{month:02d}-01')
        if month == 12:
            date_to = fields.Date.from_string(f'{year + 1}-01-01')
        else:
            date_to = fields.Date.from_string(f'{year}-{month + 1:02d}-01')
        return [
            ('effective_date', '>=', date_from),
            ('effective_date', '<', date_to),
            ('company_id', '=', self.company_id.id),
        ]

    @api.depends('month', 'year', 'company_id')
    def _compute_history_ids(self):
        History = self.env['hr.vn.si.history']
        for rec in self:
            if not rec.month or not rec.year:
                rec.history_ids = History
                rec.increase_ids = History
                rec.decrease_ids = History
                rec.adjust_ids = History
                rec.sick_maternity_ids = History
                rec.total_increase = 0
                rec.total_decrease = 0
                rec.total_adjust = 0
                rec.total_sick_maternity = 0
                continue
            domain = rec._get_history_domain()
            all_history = History.search(domain)
            rec.history_ids = all_history
            rec.increase_ids = all_history.filtered(
                lambda h: h.change_type == 'increase'
            )
            rec.decrease_ids = all_history.filtered(
                lambda h: h.change_type == 'decrease'
            )
            rec.adjust_ids = all_history.filtered(
                lambda h: h.change_type == 'adjust'
            )
            rec.sick_maternity_ids = all_history.filtered(
                lambda h: h.change_type in ('sick', 'maternity')
            )
            rec.total_increase = len(rec.increase_ids)
            rec.total_decrease = len(rec.decrease_ids)
            rec.total_adjust = len(rec.adjust_ids)
            rec.total_sick_maternity = len(rec.sick_maternity_ids)

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Chỉ xác nhận danh sách ở trạng thái Nháp.'))
            # Confirm all draft history entries for this month
            draft_history = rec.history_ids.filtered(
                lambda h: h.state == 'draft'
            )
            draft_history.action_confirm()
        self.write({'state': 'confirmed'})

    def action_draft(self):
        for rec in self:
            if rec.state == 'exported':
                raise UserError(
                    _('Không thể chuyển về Nháp khi đã xuất D02.')
                )
        self.write({'state': 'draft'})

    def action_export_d02(self):
        """Tạo báo cáo D02-LT từ danh sách này."""
        self.ensure_one()
        if self.state != 'confirmed':
            raise UserError(_('Phải xác nhận danh sách trước khi xuất D02.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Xuất báo cáo D02-LT'),
            'res_model': 'hr.vn.si.d02.export',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_monthly_list_id': self.id,
                'default_month': self.month,
                'default_year': self.year,
            },
        }
