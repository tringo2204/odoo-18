{
    'name': 'FSC Sales — Menu Planning + Customer Contracts',
    'version': '18.0.1.0.0',
    'category': 'Food Supply Chain',
    'summary': 'B2B sales planning for industrial catering: site, shift, weekly menu, customer recipe',
    'description': """
MVP 1.0 of Sales for industrial catering.

Core models:
  * catering.meal.shift     — meal shifts (breakfast/lunch/dinner/overtime/night)
  * catering.site           — customer kitchen / construction site
  * catering.customer.recipe — per-customer portion override on a meal product
  * catering.menu.plan      — weekly menu plan with state machine
  * catering.menu.plan.line — daily/shift/meal/qty rows

Extensions:
  * res.partner — fsc_default_site_id, fsc_allowed_variance_pct
  * sale.order  — site_id, meal_date, shift_id, menu_plan_id, planned/actual qty
  * sale.order.line — shift_id, customer_recipe_id, planned/actual qty

Workflow:
  1. Planning staff creates weekly menu plan for a customer/site
  2. Manager approves → state=approved
  3. Action "Generate Sales Orders" creates one SO per meal_date, lines per shift+meal
  4. SO confirms → standard Odoo MTO triggers cooking MO (via fsc_kitchen_mrp)

Deferred to MVP 1.1 / 2.0:
  * sale.order.recipe.override (one-off recipe changes per SO)
  * sale.planning.change.request (full change control with delta material demand)
  * catering.production.demand + catering.material.demand explode
  * Cut-off rules + late-change penalty
  * Customer recipe priority in mrp.bom._bom_find override
  * Approval workflows (currently: simple state machine)
  * Reports + dashboard
    """,
    'author': 'FSC',
    'depends': [
        'sale_management',
        'fsc_kitchen_mrp',
        'fsc_master_data',
    ],
    'data': [
        'security/fsc_sales_security.xml',
        'security/ir.model.access.csv',
        'data/catering_meal_shift_data.xml',
        'views/catering_meal_shift_views.xml',
        'views/catering_site_views.xml',
        'views/catering_customer_recipe_views.xml',
        'views/catering_menu_plan_views.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
        'views/menu.xml',
    ],
    'post_init_hook': '_post_init_hook',
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
