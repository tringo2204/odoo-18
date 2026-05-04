# -*- coding: utf-8 -*-
"""Migration: rename default Odoo work schedule to Vietnamese (#32)."""


def migrate(cr, version):
    cr.execute("""
        UPDATE resource_calendar
        SET name = 'Tiêu chuẩn 40 giờ/tuần'
        WHERE name = 'Standard 40 hours/week'
    """)
