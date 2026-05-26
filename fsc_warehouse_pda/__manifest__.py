{
    'name': 'FSC Warehouse PDA',
    'version': '18.0.1.0.0',
    'category': 'Food Supply Chain',
    'summary': 'PDA receipt flow + deviation capture for FSC warehouse',
    'description': """
Extends Odoo's native Barcode app for FSC warehouse:
  * fsc.receipt.deviation — captures expected vs actual qty per receipt line,
    plus reason + photo + reviewer.
  * Block flow on wrong lot / QC fail.
  * Dual confirmation hook (warehouse + downstream kitchen) — completed by
    fsc_internal_transfer.

Skeleton ships the data model + UI; barcode extensions in subsequent sprints.
    """,
    'author': 'FSC',
    'depends': [
        'fsc_master_data',
        'stock',
        'barcodes',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/fsc_receipt_deviation_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
