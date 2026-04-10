# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class ShtHrChecklistLine(models.Model):
    _name = 'sht.hr.checklist.line'
    _description = 'Employee Checklist Line'
    _order = 'sequence, id'

    name = fields.Char(required=True)
    checklist_id = fields.Many2one(
        'sht.hr.checklist', required=True, ondelete='cascade',
    )
    sequence = fields.Integer(default=10)
    responsible_role = fields.Selection([
        ('hr', 'HR'), ('manager', 'Manager'), ('it', 'IT'), ('employee', 'Employee'),
    ], default='hr', required=True)
    assigned_to = fields.Many2one('res.users', string='Người phụ trách')
    deadline_date = fields.Date(string='Hạn hoàn thành')
    is_done = fields.Boolean(default=False)
    done_by = fields.Many2one('res.users', string='Done By', readonly=True)
    done_date = fields.Date(readonly=True)
    completion_date = fields.Date(string='Ngày hoàn thành', readonly=True)
    state = fields.Selection([
        ('pending', 'Chờ xử lý'), ('in_progress', 'Đang thực hiện'),
        ('done', 'Hoàn thành'), ('cancelled', 'Đã hủy'),
    ], default='pending', required=True, string='Trạng thái')
    note = fields.Text()

    def write(self, vals):
        vals = dict(vals)
        if 'is_done' in vals:
            if vals['is_done']:
                vals.setdefault('done_by', self.env.user.id)
                vals.setdefault('done_date', fields.Date.today())
                vals.setdefault('completion_date', fields.Date.today())
                vals['state'] = 'done'
            else:
                vals.update({'done_by': False, 'done_date': False, 'completion_date': False, 'state': 'pending'})
        res = super().write(vals)
        self.mapped('checklist_id')._check_auto_complete()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('is_done'):
                vals.setdefault('done_by', self.env.user.id)
                vals.setdefault('done_date', fields.Date.today())
                vals.setdefault('completion_date', fields.Date.today())
                vals['state'] = 'done'
        return super().create(vals_list)

    def action_start(self):
        self.filtered(lambda l: l.state == 'pending').write({'state': 'in_progress'})

    def action_done(self):
        self.write({'is_done': True})

    def action_cancel(self):
        self.write({'state': 'cancelled', 'is_done': False})

    def action_reset(self):
        self.write({'state': 'pending', 'is_done': False})
