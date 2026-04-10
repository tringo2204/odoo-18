{
    'name': 'Bảo hiểm xã hội Việt Nam',
    'version': '18.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Quản lý BHXH, BHYT, BHTN — hồ sơ, tăng/giảm, D02-LT, tra cứu C12',
    'description': """
Quản lý Bảo hiểm Xã hội Việt Nam
==================================
* Hồ sơ bảo hiểm theo nhân viên
* Lịch sử biến động: tăng, giảm, điều chỉnh
* Danh sách tăng/giảm dự kiến hàng tháng
* Báo cáo D02-LT (biến động lao động)
* Tra cứu C12 (import từ cổng BHXH)
* Import lịch sử khai báo
    """,
    'author': 'SHT',
    'website': 'https://sht.vn',
    'depends': [
        'hr',
        'mail',
        'hr_payroll_vietnam',
        'sht_hr_base',
    ],
    'data': [
        # Security
        'security/hr_social_insurance_vn_security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/ir_sequence.xml',
        # Views
        'views/hr_vn_si_record_views.xml',
        'views/hr_vn_si_history_views.xml',
        'views/hr_vn_si_monthly_views.xml',
        'views/hr_vn_si_d02_views.xml',
        'views/hr_vn_si_c12_views.xml',
        'views/hr_employee_views.xml',
        # Wizards
        'wizard/si_import_history_views.xml',
        'wizard/si_c12_import_views.xml',
        'wizard/si_d02_export_views.xml',
        'wizard/si_bhxh_export_views.xml',
        # Menus (after wizards so actions exist)
        'views/menus.xml',
        # Reports
        'report/d02_lt_template.xml',
        'report/si_monthly_list.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
