# -*- coding: utf-8 -*-
# Convert sht_hr_headcount_line.year from INTEGER to VARCHAR(4)
# so Odoo never applies Vietnamese locale thousand-separator (2026 → "2.026").


def migrate(cr, version):
    cr.execute("""
        ALTER TABLE sht_hr_headcount_line
        ALTER COLUMN year TYPE VARCHAR(4) USING year::text
    """)
