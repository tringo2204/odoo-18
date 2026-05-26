import logging

_logger = logging.getLogger(__name__)


def _post_init_hook(env):
    """Create demo records when the module is installed.

    Idempotent: each lookup is keyed by default_code (products) or name
    (vendor / picking type) so re-installing the module does not duplicate.
    """
    _logger.info('FSC Demo: seeding demo data')
    vendor = _ensure_vendor(env)
    raw, semi, meal = _ensure_products(env)
    _ensure_supplierinfo(env, vendor, raw)
    _ensure_bom_semi(env, semi, raw)
    _ensure_bom_meal(env, meal, semi)
    _ensure_picking_type(env)
    _logger.info('FSC Demo: seeding complete')


def _ensure_vendor(env):
    Partner = env['res.partner']
    name = 'FSC Demo - Cong ty Rau Xanh ABC'
    vendor = Partner.search([('name', '=', name)], limit=1)
    if vendor:
        return vendor
    return Partner.create({
        'name': name,
        'is_company': True,
        'supplier_rank': 1,
        'fsc_on_time_rate': 92.0,
        'fsc_defect_rate': 3.0,
    })


def _ensure_products(env):
    Product = env['product.product']
    uom_kg = env.ref('uom.product_uom_kgm')
    uom_unit = env.ref('uom.product_uom_unit')

    raw = Product.search([('default_code', '=', 'FSC-RAW-RAUMUONG')], limit=1)
    if not raw:
        raw = Product.create({
            'name': 'FSC Demo - Rau muong tuoi',
            'default_code': 'FSC-RAW-RAUMUONG',
            'type': 'consu',
            'is_storable': True,
            'uom_id': uom_kg.id,
            'uom_po_id': uom_kg.id,
            'fsc_product_type': 'raw',
            'fsc_processing_type': 'none',
            'standard_price': 15000.0,
            'list_price': 20000.0,
        })

    semi = Product.search([('default_code', '=', 'FSC-SEMI-RAUMUONG')], limit=1)
    if not semi:
        semi = Product.create({
            'name': 'FSC Demo - Rau muong sach (so che)',
            'default_code': 'FSC-SEMI-RAUMUONG',
            'type': 'consu',
            'is_storable': True,
            'uom_id': uom_kg.id,
            'uom_po_id': uom_kg.id,
            'fsc_product_type': 'semi_finished',
            'fsc_processing_type': 'preprocess',
            'fsc_yield_expected': 85.0,
            'fsc_loss_threshold': 15.0,
            'standard_price': 22000.0,
        })

    meal = Product.search([('default_code', '=', 'FSC-MEAL-COMRAUMUONG')], limit=1)
    if not meal:
        meal = Product.create({
            'name': 'FSC Demo - Com rau muong',
            'default_code': 'FSC-MEAL-COMRAUMUONG',
            'type': 'consu',
            'is_storable': True,
            'uom_id': uom_unit.id,
            'uom_po_id': uom_unit.id,
            'fsc_product_type': 'finished',
            'fsc_processing_type': 'cooking',
            'standard_price': 35000.0,
            'list_price': 50000.0,
        })

    return raw, semi, meal


def _ensure_supplierinfo(env, vendor, product):
    Supplier = env['product.supplierinfo']
    existing = Supplier.search([
        ('partner_id', '=', vendor.id),
        ('product_id', '=', product.id),
    ], limit=1)
    if existing:
        return existing
    return Supplier.create({
        'partner_id': vendor.id,
        'product_tmpl_id': product.product_tmpl_id.id,
        'product_id': product.id,
        'price': 20000.0,
        'min_qty': 0.0,
        'product_uom': product.uom_id.id,
    })


def _ensure_bom_semi(env, semi, raw):
    """BOM: 1 kg semi requires 1.18 kg raw (expected loss 15%)."""
    Bom = env['mrp.bom']
    existing = Bom.search([
        ('product_tmpl_id', '=', semi.product_tmpl_id.id),
        ('type', '=', 'normal'),
    ], limit=1)
    if existing:
        return existing
    return Bom.create({
        'product_tmpl_id': semi.product_tmpl_id.id,
        'product_qty': 1.0,
        'product_uom_id': semi.uom_id.id,
        'type': 'normal',
        'fsc_expected_yield': 85.0,
        'fsc_expected_loss': 15.0,
        'fsc_processing_time': 0.5,
        'bom_line_ids': [(0, 0, {
            'product_id': raw.id,
            'product_qty': 1.18,
            'product_uom_id': raw.uom_id.id,
        })],
    })


def _ensure_bom_meal(env, meal, semi):
    """BOM: 1 portion of meal requires 0.15 kg semi."""
    Bom = env['mrp.bom']
    existing = Bom.search([
        ('product_tmpl_id', '=', meal.product_tmpl_id.id),
        ('type', '=', 'normal'),
    ], limit=1)
    if existing:
        return existing
    return Bom.create({
        'product_tmpl_id': meal.product_tmpl_id.id,
        'product_qty': 1.0,
        'product_uom_id': meal.uom_id.id,
        'type': 'normal',
        'bom_line_ids': [(0, 0, {
            'product_id': semi.id,
            'product_qty': 0.15,
            'product_uom_id': semi.uom_id.id,
        })],
    })


def _ensure_picking_type(env):
    """A WH → Kitchen picking type pre-flagged for dual confirmation."""
    PickingType = env['stock.picking.type']
    existing = PickingType.search([('name', '=', 'FSC Demo - WH to Kitchen')], limit=1)
    if existing:
        return existing
    warehouse = env['stock.warehouse'].search(
        [('company_id', '=', env.company.id)], limit=1)
    Location = env['stock.location']
    kitchen = Location.search([('name', '=', 'FSC Demo Kitchen')], limit=1)
    if not kitchen:
        kitchen = Location.create({
            'name': 'FSC Demo Kitchen',
            'usage': 'internal',
            'location_id': warehouse.view_location_id.id,
            'company_id': env.company.id,
        })
    return PickingType.create({
        'name': 'FSC Demo - WH to Kitchen',
        'code': 'internal',
        'sequence_code': 'FSC/',
        'warehouse_id': warehouse.id,
        'default_location_src_id': warehouse.lot_stock_id.id,
        'default_location_dest_id': kitchen.id,
        'fsc_dual_confirm': True,
    })
