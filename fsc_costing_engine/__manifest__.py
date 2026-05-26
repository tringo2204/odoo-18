{
    'name': 'FSC Costing Engine',
    'version': '18.0.1.0.0',
    'category': 'Food Supply Chain',
    'summary': 'Precise preprocess + meal costing with variance analysis',
    'description': """
Costing layer:
  * fsc.meal.cost — per-MO meal cost record (planned vs actual, breakdown,
    cost per meal, variance).
  * mrp.production.button_mark_done() hook: when a finished-product MO is done,
    auto-create an aggregate meal-cost record. Raw cost is computed from
    move_raw_ids × standard_price. Planned cost is computed from the BOM scaled
    to MO qty. Labor + overhead default to 0 (to be filled by work-order /
    analytic integration in a later sprint).
    """,
    'author': 'FSC',
    'depends': [
        'fsc_master_data',
        'mrp_account',
        'stock_account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/fsc_meal_cost_views.xml',
        'views/mrp_production_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
