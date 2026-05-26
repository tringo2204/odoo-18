{
    'name': 'FSC Internal Transfer',
    'version': '18.0.1.0.0',
    'category': 'Food Supply Chain',
    'summary': 'WH ↔ Kitchen dual confirmation transfers',
    'description': """
Dual confirmation flow for warehouse-to-kitchen internal transfers:
  * stock.picking.type.fsc_dual_confirm flag opts a picking type into dual confirm.
  * stock.move snapshot fields fsc_warehouse_qty and fsc_kitchen_qty.
  * stock.picking actions:
    - action_fsc_warehouse_confirm: snapshots dispatched qty per move.
    - action_fsc_kitchen_confirm: snapshots received qty + auto-creates
      fsc.transfer.discrepancy records for any mismatch.
  * button_validate is blocked until both confirmations are recorded.
    """,
    'author': 'FSC',
    'depends': [
        'fsc_master_data',
        'fsc_warehouse_pda',
        'stock',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/fsc_transfer_discrepancy_views.xml',
        'views/stock_picking_type_views.xml',
        'views/stock_picking_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
