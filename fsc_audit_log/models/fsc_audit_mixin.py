from odoo import api, models


class FscAuditMixin(models.AbstractModel):
    _name = 'fsc.audit.mixin'
    _description = 'FSC Audit Mixin'

    # Override in concrete models. Empty = no fields tracked.
    _fsc_audit_fields = ()

    def _fsc_log(self, action, field_name=False, old_value=False, new_value=False, reason=False):
        self.ensure_one()
        return self.env['fsc.audit.log'].sudo().create({
            'model_name': self._name,
            'res_id': self.id,
            'action': action,
            'field_name': field_name or False,
            'old_value': False if old_value is False else str(old_value),
            'new_value': False if new_value is False else str(new_value),
            'reason': reason or '/',
            'user_id': self.env.uid,
        })

    def write(self, vals):
        # Concrete subclasses can pop 'fsc_audit_reason' from context to provide a reason.
        tracked = [f for f in self._fsc_audit_fields if f in vals]
        if not tracked:
            return super().write(vals)
        reason = self.env.context.get('fsc_audit_reason') or vals.pop('fsc_audit_reason', None)
        before = {rec.id: {f: rec[f] for f in tracked} for rec in self}
        res = super().write(vals)
        Log = self.env['fsc.audit.log'].sudo()
        for rec in self:
            for f in tracked:
                old = before[rec.id][f]
                new = rec[f]
                if old != new:
                    Log.create({
                        'model_name': rec._name,
                        'res_id': rec.id,
                        'action': 'write',
                        'field_name': f,
                        'old_value': str(old) if old is not False else False,
                        'new_value': str(new) if new is not False else False,
                        'reason': reason or '/',
                        'user_id': self.env.uid,
                    })
        return res
