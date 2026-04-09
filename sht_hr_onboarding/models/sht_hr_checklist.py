# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ShtHrChecklist(models.Model):
    _name = 'sht.hr.checklist'
    _description = 'Employee Checklist'
    _order = 'date_start desc, id desc'

    name = fields.Char(compute='_compute_name', store=True, readonly=True)
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
    template_id = fields.Many2one('sht.hr.checklist.template', ondelete='set null')
    checklist_type = fields.Selection(
        [('onboarding', 'Onboarding'), ('offboarding', 'Offboarding')],
        required=True,
    )
    line_ids = fields.One2many('sht.hr.checklist.line', 'checklist_id', string='Lines')
    progress = fields.Float(compute='_compute_progress', string='Progress')
    state = fields.Selection(
        [
            ('in_progress', 'In Progress'),
            ('done', 'Done'),
            ('cancelled', 'Cancelled'),
        ],
        default='in_progress',
        required=True,
    )
    date_start = fields.Date(default=fields.Date.today)
    date_completed = fields.Date()
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
    )

    @api.depends('checklist_type', 'employee_id', 'employee_id.name')
    def _compute_name(self):
        labels = dict(self._fields['checklist_type'].selection)
        for rec in self:
            label = labels.get(rec.checklist_type, '')
            if rec.employee_id:
                rec.name = '%s - %s' % (label, rec.employee_id.name or '')
            else:
                rec.name = label

    @api.depends('line_ids.is_done')
    def _compute_progress(self):
        for rec in self:
            lines = rec.line_ids
            if not lines:
                rec.progress = 0.0
            else:
                done = sum(1 for line in lines if line.is_done)
                rec.progress = 100.0 * done / len(lines)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('employee_id') and not vals.get('company_id'):
                employee = self.env['hr.employee'].browse(vals['employee_id'])
                vals['company_id'] = employee.company_id.id
        return super().create(vals_list)

    def action_generate_lines(self):
        for checklist in self:
            if not checklist.template_id:
                raise UserError(_('Set a checklist template before generating lines.'))
            checklist.line_ids.unlink()
            line_vals = []
            for tmpl_line in checklist.template_id.line_ids.sorted('sequence'):
                line_vals.append((0, 0, {
                    'name': tmpl_line.name,
                    'sequence': tmpl_line.sequence,
                    'responsible_role': tmpl_line.responsible_role,
                }))
            checklist.write({
                'line_ids': line_vals,
                'checklist_type': checklist.template_id.checklist_type,
            })
        return True

    def action_mark_done(self):
        todo = self.filtered(lambda c: c.state == 'in_progress')
        todo.write({
            'state': 'done',
            'date_completed': fields.Date.today(),
        })
        return True

    def action_cancel(self):
        self.write({'state': 'cancelled'})
        return True
