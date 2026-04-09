from odoo.tests import TransactionCase, tagged
from odoo.exceptions import UserError


@tagged('post_install', '-at_install')
class TestHrVnDecision(TransactionCase):
    """Test HR decision application logic."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.department_a = cls.env['hr.department'].create({'name': 'Dept A'})
        cls.department_b = cls.env['hr.department'].create({'name': 'Dept B'})
        cls.job_dev = cls.env['hr.job'].create({'name': 'Developer'})
        cls.job_lead = cls.env['hr.job'].create({'name': 'Team Lead'})

        cls.employee = cls.env['hr.employee'].create({
            'name': 'Test Decision Employee',
            'department_id': cls.department_a.id,
            'job_id': cls.job_dev.id,
        })
        cls.contract = cls.env['hr.contract'].create({
            'name': 'Test Contract',
            'employee_id': cls.employee.id,
            'wage': 15_000_000,
            'state': 'open',
            'date_start': '2024-01-01',
        })

    def _create_decision(self, decision_type, **kwargs):
        vals = {
            'employee_id': self.employee.id,
            'decision_type': decision_type,
            'effective_date': '2025-06-01',
        }
        vals.update(kwargs)
        return self.env['hr.vn.decision'].create(vals)

    def test_sequence_on_create(self):
        decision = self._create_decision('appointment')
        self.assertNotEqual(decision.name, 'Mới')

    def test_workflow_states(self):
        decision = self._create_decision('appointment')
        self.assertEqual(decision.state, 'draft')

        decision.action_confirm()
        self.assertEqual(decision.state, 'confirmed')

        decision.action_done()
        self.assertEqual(decision.state, 'done')

    def test_cancel_and_reset(self):
        decision = self._create_decision('appointment')
        decision.action_confirm()
        decision.action_cancel()
        self.assertEqual(decision.state, 'cancelled')

        decision.action_draft()
        self.assertEqual(decision.state, 'draft')

    def test_transfer_updates_department_and_job(self):
        decision = self._create_decision('transfer',
                                         department_id=self.department_b.id,
                                         job_id=self.job_lead.id)
        decision.action_confirm()
        decision.action_done()

        self.assertEqual(self.employee.department_id, self.department_b)
        self.assertEqual(self.employee.job_id, self.job_lead)

    def test_appointment_updates_job(self):
        decision = self._create_decision('appointment',
                                         job_id=self.job_lead.id)
        decision.action_confirm()
        decision.action_done()

        self.assertEqual(self.employee.job_id, self.job_lead)

    def test_salary_adjustment_updates_contract(self):
        decision = self._create_decision('salary_adjustment',
                                         old_wage=15_000_000,
                                         new_wage=20_000_000)
        decision.action_confirm()
        decision.action_done()

        self.assertEqual(self.contract.wage, 20_000_000)

    def test_salary_adjustment_no_contract_raises(self):
        emp_no_contract = self.env['hr.employee'].create({
            'name': 'No Contract Employee',
        })
        decision = self._create_decision('salary_adjustment',
                                         employee_id=emp_no_contract.id,
                                         new_wage=20_000_000)
        decision.action_confirm()
        with self.assertRaises(UserError):
            decision.action_done()

    def test_termination_sets_departure_date(self):
        decision = self._create_decision('termination',
                                         effective_date='2025-12-31')
        decision.action_confirm()
        decision.action_done()

        from odoo.fields import Date
        self.assertEqual(self.employee.departure_date, Date.from_string('2025-12-31'))
