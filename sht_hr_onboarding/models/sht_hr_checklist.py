# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ShtHrChecklist(models.Model):
    _name = 'sht.hr.checklist'
    _description = 'Employee Checklist'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc, id desc'
    _check_company_auto = True

    name = fields.Char(compute='_compute_name', store=True, readonly=True)
    employee_id = fields.Many2one(
        'hr.employee', required=True, ondelete='cascade', tracking=True,
    )
    department_id = fields.Many2one(
        'hr.department', related='employee_id.department_id', store=True,
    )
    template_id = fields.Many2one('sht.hr.checklist.template', ondelete='set null')
    checklist_type = fields.Selection([
        ('onboarding', 'Onboarding'), ('offboarding', 'Offboarding'),
    ], required=True, tracking=True)
    line_ids = fields.One2many('sht.hr.checklist.line', 'checklist_id', string='Lines')
    progress = fields.Float(compute='_compute_progress', store=True)
    total_tasks = fields.Integer(compute='_compute_progress', store=True)
    done_tasks = fields.Integer(compute='_compute_progress', store=True)
    state = fields.Selection([
        ('in_progress', 'In Progress'), ('done', 'Done'), ('cancelled', 'Cancelled'),
    ], default='in_progress', required=True, tracking=True)
    date_start = fields.Date(default=fields.Date.today)
    date_completed = fields.Date()
    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company,
    )

    @api.depends('checklist_type', 'employee_id', 'employee_id.name')
    def _compute_name(self):
        labels = dict(self._fields['checklist_type'].selection)
        for rec in self:
            label = labels.get(rec.checklist_type, '')
            rec.name = '%s - %s' % (label, rec.employee_id.name or '') if rec.employee_id else label

    @api.depends('line_ids.is_done', 'line_ids.state')
    def _compute_progress(self):
        for rec in self:
            lines = rec.line_ids.filtered(lambda l: l.state != 'cancelled')
            rec.total_tasks = len(lines)
            rec.done_tasks = len(lines.filtered(lambda l: l.is_done))
            rec.progress = 100.0 * rec.done_tasks / len(lines) if lines else 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('employee_id') and not vals.get('company_id'):
                employee = self.env['hr.employee'].browse(vals['employee_id']).exists()
                if employee:
                    vals['company_id'] = employee.company_id.id
        return super().create(vals_list)

    def action_generate_lines(self):
        for checklist in self:
            if not checklist.template_id:
                raise UserError(_('Set a checklist template before generating lines.'))
            checklist.line_ids.unlink()
            line_vals = []
            for tmpl_line in checklist.template_id.line_ids.sorted('sequence'):
                deadline = False
                if tmpl_line.default_deadline_days and checklist.date_start:
                    deadline = checklist.date_start + timedelta(days=tmpl_line.default_deadline_days)
                line_vals.append((0, 0, {
                    'name': tmpl_line.name,
                    'sequence': tmpl_line.sequence,
                    'responsible_role': tmpl_line.responsible_role,
                    'deadline_date': deadline,
                    'state': 'pending',
                }))
            checklist.write({'line_ids': line_vals, 'checklist_type': checklist.template_id.checklist_type})

    def action_mark_done(self):
        todo = self.filtered(lambda c: c.state == 'in_progress')
        todo.write({'state': 'done', 'date_completed': fields.Date.today()})
        for rec in todo:
            labels = dict(self._fields['checklist_type'].selection)
            label = labels.get(rec.checklist_type, '')
            rec.message_post(
                body=_('%s hoàn thành cho %s.') % (label, rec.employee_id.name),
                subtype_xmlid='mail.mt_comment',
            )
            # Notify HR manager
            if rec.employee_id.parent_id and rec.employee_id.parent_id.user_id:
                rec.activity_schedule(
                    act_type_xmlid='mail.mail_activity_data_todo',
                    summary=_('%s hoàn thành') % label,
                    user_id=rec.employee_id.parent_id.user_id.id,
                )

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def _check_auto_complete(self):
        for rec in self:
            if rec.state != 'in_progress':
                continue
            active_lines = rec.line_ids.filtered(lambda l: l.state != 'cancelled')
            if active_lines and all(l.is_done for l in active_lines):
                rec.action_mark_done()
