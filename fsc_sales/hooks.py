import logging
from datetime import timedelta

from odoo import fields

_logger = logging.getLogger(__name__)


def _post_init_hook(env):
    _logger.info('FSC Sales: seeding sequences + demo data')
    _ensure_sequences(env)
    _ensure_demo_customer_site_recipe_menu(env)
    _logger.info('FSC Sales: seeding complete')


def _ensure_sequences(env):
    Sequence = env['ir.sequence']
    for code, prefix in [
        ('catering.customer.recipe', 'CR/%(year)s/'),
        ('catering.menu.plan', 'MP/%(year)s/%(month)s/'),
    ]:
        if not Sequence.search([('code', '=', code)], limit=1):
            Sequence.create({
                'name': code,
                'code': code,
                'prefix': prefix,
                'padding': 5,
                'company_id': False,
            })


def _ensure_demo_customer_site_recipe_menu(env):
    """Idempotent demo: 1 customer + 1 site + 1 customer recipe + 1 week menu."""
    Partner = env['res.partner']
    Site = env['catering.site']
    MenuPlan = env['catering.menu.plan']
    Recipe = env['catering.customer.recipe']
    Product = env['product.product']

    # 1) Customer
    customer = Partner.search([('name', '=', 'FSC Sales Demo - Cong ty May ABC')], limit=1)
    if not customer:
        customer = Partner.create({
            'name': 'FSC Sales Demo - Cong ty May ABC',
            'is_company': True,
            'customer_rank': 1,
            'street': 'KCN Sai Dong, Long Bien',
            'city': 'Ha Noi',
            'fsc_allowed_variance_qty': 100,
            'fsc_allowed_variance_pct': 10.0,
        })

    # 2) Site (mapped to a stock location under main warehouse)
    site = Site.search([('name', '=', 'Bep Cty May ABC'),
                        ('customer_id', '=', customer.id)], limit=1)
    if not site:
        warehouse = env['stock.warehouse'].search(
            [('company_id', '=', env.company.id)], limit=1)
        kitchen_loc = env['stock.location'].search(
            [('name', '=', 'FSC Demo Kitchen')], limit=1)
        if not kitchen_loc:
            kitchen_loc = env['stock.location'].create({
                'name': 'Bep Cty May ABC Kitchen',
                'usage': 'internal',
                'location_id': warehouse.view_location_id.id,
            })
        shifts = env['catering.meal.shift'].search(
            [('code', 'in', ['BREAKFAST', 'LUNCH', 'DINNER'])])
        site = Site.create({
            'name': 'Bep Cty May ABC',
            'code': 'KITCHEN-ABC',
            'customer_id': customer.id,
            'warehouse_id': warehouse.id,
            'location_id': kitchen_loc.id,
            'meal_shift_ids': [(6, 0, shifts.ids)],
            'default_delivery_time': 11.0,
        })

    if not customer.fsc_default_site_id:
        customer.fsc_default_site_id = site

    # 3) Customer recipe — override portion of "Com rau muong"
    meal = Product.search([('default_code', '=', 'FSC-MEAL-COMRAUMUONG')], limit=1)
    semi_rau = Product.search([('default_code', '=', 'FSC-SEMI-RAUMUONG')], limit=1)
    if meal and semi_rau:
        recipe = Recipe.search([
            ('customer_id', '=', customer.id),
            ('meal_product_id', '=', meal.id),
        ], limit=1)
        if not recipe:
            recipe = Recipe.create({
                'customer_id': customer.id,
                'site_id': site.id,
                'meal_product_id': meal.id,
                'effective_from': fields.Date.context_today(env.user),
                'state': 'active',
                'line_ids': [(0, 0, {
                    'ingredient_id': semi_rau.id,
                    'qty_per_serving': 0.18,   # 30% more than master 0.15 kg
                    'uom_id': semi_rau.uom_id.id,
                    'note': 'Customer ABC yeu cau dinh luong rau lon hon mac dinh',
                })],
            })

    # 4) Sample weekly menu plan
    plan = MenuPlan.search([
        ('customer_id', '=', customer.id),
        ('site_id', '=', site.id),
    ], limit=1, order='week_start_date desc')
    if plan:
        return  # Already seeded.

    today = fields.Date.context_today(env.user)
    next_monday = today + timedelta(days=(7 - today.weekday()) % 7 or 7)

    plan = MenuPlan.create({
        'customer_id': customer.id,
        'site_id': site.id,
        'week_start_date': next_monday,
        'state': 'draft',
        'notes': 'Demo menu tuan mau cho Cong ty May ABC.',
    })

    shift_lunch = env.ref('fsc_sales.shift_lunch', raise_if_not_found=False)
    shift_dinner = env.ref('fsc_sales.shift_dinner', raise_if_not_found=False)
    meals_by_code = {
        p.default_code: p for p in Product.search(
            [('default_code', 'in', [
                'FSC-MEAL-COMRAUMUONG', 'FSC-MEAL-COMTHITKHO',
                'FSC-MEAL-COMGAOXOIMO', 'FSC-MEAL-RAUTRON',
            ])])
    }

    weekly_lunch_rotation = [
        'FSC-MEAL-COMRAUMUONG', 'FSC-MEAL-COMTHITKHO',
        'FSC-MEAL-COMGAOXOIMO', 'FSC-MEAL-COMRAUMUONG',
        'FSC-MEAL-COMTHITKHO',
    ]
    lines = []
    for day_idx in range(5):  # Mon-Fri
        date = next_monday + timedelta(days=day_idx)
        # Lunch
        if shift_lunch and meals_by_code.get(weekly_lunch_rotation[day_idx]):
            lines.append((0, 0, {
                'meal_date': date,
                'shift_id': shift_lunch.id,
                'meal_product_id': meals_by_code[weekly_lunch_rotation[day_idx]].id,
                'planned_qty': 1200,
                'customer_recipe_id': recipe.id if recipe and meals_by_code[weekly_lunch_rotation[day_idx]] == meal else False,
            }))
        # Dinner
        if shift_dinner and meals_by_code.get('FSC-MEAL-RAUTRON'):
            lines.append((0, 0, {
                'meal_date': date,
                'shift_id': shift_dinner.id,
                'meal_product_id': meals_by_code['FSC-MEAL-RAUTRON'].id,
                'planned_qty': 700,
            }))
    plan.line_ids = lines
