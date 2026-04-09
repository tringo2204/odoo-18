# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ShtHrTraining(models.Model):
    _name = 'sht.hr.training'
    _description = 'Employee Training Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc, id desc'

    name = fields.Char(compute='_compute_name', store=True)
    employee_id = fields.Many2one(
        'hr.employee',
        required=True,
        ondelete='cascade',
    )
    department_id = fields.Many2one(
        'hr.department',
        related='employee_id.department_id',
        store=True,
        readonly=True,
    )
    course_id = fields.Many2one(
        'sht.hr.training.course',
        required=True,
        ondelete='restrict',
    )
    date_start = fields.Date(required=True)
    date_end = fields.Date()
    state = fields.Selection(
        [
            ('planned', 'Planned'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled'),
        ],
        default='planned',
        tracking=True,
    )
    result = fields.Selection(
        [
            ('pass', 'Pass'),
            ('fail', 'Fail'),
            ('na', 'N/A'),
        ],
        default='na',
    )
    score = fields.Float()
    certificate_attachment = fields.Binary(attachment=True)
    certificate_filename = fields.Char()
    note = fields.Text()
    cost = fields.Float(string='Cost (VND)')
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        required=True,
    )

    @api.depends('course_id', 'employee_id')
    def _compute_name(self):
        for rec in self:
            parts = []
            if rec.course_id:
                parts.append(rec.course_id.name or '')
            if rec.employee_id:
                parts.append(rec.employee_id.name or '')
            rec.name = ' - '.join(parts) if parts else ''

    @api.constrains('date_start', 'date_end')
    def _check_date_end(self):
        for rec in self:
            if rec.date_start and rec.date_end and rec.date_end < rec.date_start:
                raise ValidationError(
                    _('End date must be on or after the start date.')
                )

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_complete(self):
        self.write({'state': 'completed'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})
