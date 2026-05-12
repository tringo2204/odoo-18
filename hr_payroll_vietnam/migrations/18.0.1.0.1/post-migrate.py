# -*- coding: utf-8 -*-
"""Row 203: rename existing dashboard note records to Vietnamese."""


def migrate(cr, version):
    cr.execute("""
        UPDATE hr_payroll_note
        SET name = 'Ghi chú'
        WHERE name = 'Note'
    """)
    cr.execute("""
        UPDATE hr_payroll_note
        SET name = 'Chưa đặt tên'
        WHERE name = 'Untitled'
    """)
