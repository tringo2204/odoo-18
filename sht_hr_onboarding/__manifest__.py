# -*- coding: utf-8 -*-
{
    'name': 'HR Onboarding / Offboarding Checklists',
    'version': '18.0.2.0.0',
    'category': 'Human Resources',
    'summary': 'Template-based onboarding and offboarding checklists per employee',
    'depends': ['hr', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/offboarding_templates.xml',
        'views/sht_hr_checklist_template_views.xml',
        'views/sht_hr_checklist_views.xml',
        'views/sht_hr_offboarding_views.xml',
        'views/hr_employee_views.xml',
        'views/menu.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
