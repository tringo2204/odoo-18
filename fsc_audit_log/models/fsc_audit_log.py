from odoo import api, fields, models


class FscAuditLog(models.Model):
    _name = 'fsc.audit.log'
    _description = 'FSC Audit Log'
    _order = 'create_date desc, id desc'
    _rec_name = 'display_name'

    model_name = fields.Char(string='Model', required=True, index=True)
    res_id = fields.Integer(string='Record ID', required=True, index=True)
    res_ref = fields.Reference(
        string='Record',
        selection='_referencable_models',
        compute='_compute_res_ref',
    )
    action = fields.Selection(
        [('create', 'Create'), ('write', 'Write'), ('unlink', 'Unlink')],
        string='Action', required=True,
    )
    field_name = fields.Char(string='Field')
    old_value = fields.Text(string='Old Value')
    new_value = fields.Text(string='New Value')
    reason = fields.Text(string='Reason', required=True)
    user_id = fields.Many2one('res.users', string='User', required=True,
                              default=lambda self: self.env.user, index=True)
    display_name = fields.Char(compute='_compute_display_name_field', store=False)

    @api.model
    def _referencable_models(self):
        return [(m.model, m.name) for m in self.env['ir.model'].sudo().search([])]

    @api.depends('model_name', 'res_id')
    def _compute_res_ref(self):
        for log in self:
            if log.model_name and log.res_id and log.model_name in self.env:
                log.res_ref = f'{log.model_name},{log.res_id}'
            else:
                log.res_ref = False

    @api.depends('model_name', 'res_id', 'action', 'field_name')
    def _compute_display_name_field(self):
        for log in self:
            parts = [log.model_name or '?', f'#{log.res_id}', log.action or '']
            if log.field_name:
                parts.append(log.field_name)
            log.display_name = ' / '.join(p for p in parts if p)
