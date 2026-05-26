{
    'name': 'FSC Kitchen MRP',
    'version': '18.0.1.0.0',
    'category': 'Food Supply Chain',
    'summary': 'Cooking MO + meal output tracking + auto-replenish on shortage',
    'description': """
Kitchen MRP layer (depends on preprocess MRP + procurement engine):
  * fsc.cooking.batch — tracks a cooking MO with kitchen location, batch size,
    expected vs actual meal output, shortage flag.
  * mrp.production extension:
    - Auto-create cooking batch on MO creation for fsc_processing_type='cooking'.
    - Detect raw shortage on confirm() → flag batch + post chatter + create
      urgent fsc.consolidation.line in state='open' for immediate procurement.
    - Finalize batch (actual qty + state='done') on button_mark_done().
    """,
    'author': 'FSC',
    'depends': [
        'fsc_preprocess_mrp',
        'fsc_procurement_engine',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/fsc_cooking_batch_views.xml',
        'views/mrp_production_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
