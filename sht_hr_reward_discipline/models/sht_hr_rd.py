# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ShtHrRd(models.Model):
    _name = 'sht.hr.rd'
    _description = 'Reward & Discipline Record'
    _order = 'date desc, id desc'
    _inherit = ['mail.thread']

    name = fields.Char(required=True, default='New', copy=False)
    employee_id = fields.Many2one(
        'hr.employee',
        string='Nhân viên',
        required=True,
        ondelete='restrict',
        tracking=True,
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Phòng ban',
        related='employee_id.department_id',
        store=True,
        readonly=True,
    )
    rd_type_id = fields.Many2one(
        'sht.hr.rd.type',
        string='Loại',
        required=True,
        ondelete='restrict',
        tracking=True,
    )
    # Standalone field (not related) so default_category context works
    category = fields.Selection(
        [('reward', 'Khen thưởng'), ('discipline', 'Kỷ luật')],
        string='Phân loại',
        store=True,
        tracking=True,
    )

    @api.onchange('rd_type_id')
    def _onchange_rd_type_id(self):
        if self.rd_type_id:
            self.category = self.rd_type_id.category
    date = fields.Date(required=True, default=fields.Date.today, tracking=True)
    decision_number = fields.Char(string='Decision No.')
    decision_date = fields.Date(string='Decision Date')
    amount = fields.Float(string='Amount (VND)')
    reason = fields.Text(required=True)
    description = fields.Html()
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('confirmed', 'Confirmed'),
            ('cancelled', 'Cancelled'),
        ],
        default='draft',
        tracking=True,
    )
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        required=True,
    )

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in (False, 'New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('sht.hr.rd') or 'New'
        return super().create(vals_list)
