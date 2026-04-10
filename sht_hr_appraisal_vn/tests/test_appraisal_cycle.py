from datetime import date
from odoo.tests.common import TransactionCase


class TestAppraisalCycle(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dept = cls.env['hr.department'].create({'name': 'Test Dept'})
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Test Employee',
            'department_id': cls.dept.id,
        })
        cls.criteria_1 = cls.env['sht.hr.appraisal.criteria'].create({
            'name': 'Tinh thần', 'category': 'attitude', 'weight': 50,
        })
        cls.criteria_2 = cls.env['sht.hr.appraisal.criteria'].create({
            'name': 'Kỹ năng', 'category': 'skill', 'weight': 50,
        })
        cls.template = cls.env['sht.hr.appraisal.template'].create({
            'name': 'Template Test',
            'criteria_ids': [(6, 0, [cls.criteria_1.id, cls.criteria_2.id])],
        })

    def test_cycle_generate_appraisals(self):
        cycle = self.env['sht.hr.appraisal.cycle'].create({
            'date_from': date(2024, 1, 1),
            'date_to': date(2024, 3, 31),
            'period_type': 'quarterly',
            'department_ids': [(6, 0, [self.dept.id])],
            'template_id': self.template.id,
        })
        cycle.action_start()
        self.assertEqual(cycle.state, 'in_progress')

        cycle.action_generate_appraisals()
        self.assertEqual(cycle.total_count, 1)
        appraisal = cycle.appraisal_ids[0]
        self.assertEqual(appraisal.employee_id, self.employee)
        self.assertEqual(len(appraisal.line_ids), 2)

    def test_overall_score_computation(self):
        cycle = self.env['sht.hr.appraisal.cycle'].create({
            'date_from': date(2024, 1, 1),
            'date_to': date(2024, 3, 31),
            'period_type': 'quarterly',
            'template_id': self.template.id,
        })
        cycle.action_start()
        cycle.action_generate_appraisals()
        appraisal = cycle.appraisal_ids[0]

        # Set scores
        for line in appraisal.line_ids:
            line.write({'manager_score': 4.0})

        self.assertAlmostEqual(appraisal.overall_score, 4.0, places=1)
        self.assertEqual(appraisal.rating, 'good')
