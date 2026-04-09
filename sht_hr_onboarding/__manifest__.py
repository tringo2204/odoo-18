# -*- coding: utf-8 -*-
{
    'name': 'HR Onboarding / Offboarding Checklists',
    'version': '18.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Template-based onboarding and offboarding checklists per employee',
    'depends': ['hr'],
    'data': [
        'security/ir.model.access.csv',
        'views/sht_hr_checklist_template_views.xml',
        'views/sht_hr_checklist_views.xml',
        'views/hr_employee_views.xml',
        'views/menu.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
