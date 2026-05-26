{
    'name': 'FSC Audit Log',
    'version': '18.0.1.0.0',
    'category': 'Food Supply Chain',
    'summary': 'Mandatory reason capture + change log mixin for FSC modules',
    'description': """
Provides:
  * fsc.audit.mixin — mixin to attach onto FSC models that must record every change
    to whitelisted fields with a mandatory reason.
  * fsc.audit.log — append-only log of changes (model, record, field, old, new, reason, user, ts).

Other fsc_* modules inherit fsc.audit.mixin and declare _fsc_audit_fields = [...]
to enable change capture on specific fields.
    """,
    'author': 'FSC',
    'depends': ['base', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/fsc_audit_log_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
