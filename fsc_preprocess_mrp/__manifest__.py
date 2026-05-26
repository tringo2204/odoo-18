{
    'name': 'FSC Preprocess MRP',
    'version': '18.0.1.0.0',
    'category': 'Food Supply Chain',
    'summary': 'Preprocess MO auto-trigger + per-stage loss tracking',
    'description': """
Preprocess MRP layer:
  * fsc.loss.record — per-MO per-stage loss capture with computed loss_qty and
    over-threshold flag.
  * mrp.production.button_mark_done() override: when a preprocess MO is marked
    done, automatically create an aggregate loss record. If actual loss exceeds
    BOM/product threshold, post an alert on the MO chatter.
  * Standard Odoo MRP routes drive the auto-trigger of preprocess MOs from
    kitchen demand — no override needed there, only correct route configuration.
    """,
    'author': 'FSC',
    'depends': [
        'fsc_master_data',
        'mrp',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/fsc_loss_record_views.xml',
        'views/mrp_production_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
