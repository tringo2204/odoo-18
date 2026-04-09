# -*- coding: utf-8 -*-
{
    'name': 'SHT HR Recruitment',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Recruitment',
    'summary': 'Headcount planning and recruitment extensions',
    'depends': ['hr_recruitment'],
    'data': [
        'security/ir.model.access.csv',
        'views/sht_hr_headcount_plan_views.xml',
        'views/hr_applicant_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
