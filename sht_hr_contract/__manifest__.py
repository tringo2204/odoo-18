# -*- coding: utf-8 -*-
{
    'name': 'SHT Vietnam HR Contract',
    'version': '18.0.1.0.1',
    'category': 'Human Resources/Contracts',
    'summary': 'Vietnam-specific contract types, probation, renewal alerts, termination',
    'depends': ['hr_contract'],
    'data': [
        'security/ir.model.access.csv',
        'data/sht_hr_contract_type_data.xml',
        'data/vn_calendar_rename.xml',
        'views/sht_hr_contract_type_views.xml',
        'views/hr_contract_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
    'post_init_hook': 'post_init_hook',
}
