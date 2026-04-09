from odoo.tests import TransactionCase, tagged
from odoo.exceptions import UserError, ValidationError


@tagged('post_install', '-at_install')
class TestHrRequestWorkflow(TransactionCase):
    """Test the HR request approval workflow."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Test Employee',
        })
        cls.manager_user = cls.env['res.users'].create({
            'name': 'Test Manager',
            'login': 'test_manager_req',
            'groups_id': [(4, cls.env.ref('hr.group_hr_manager').id)],
        })
        cls.manager_employee = cls.env['hr.employee'].create({
            'name': 'Test Manager Employee',
            'user_id': cls.manager_user.id,
        })
        cls.employee.write({'parent_id': cls.manager_employee.id})

        cls.request_type_ot = cls.env.ref('hr_request_vn.request_type_ot')
        cls.request_type_ot.write({
            'approval_rule_ids': [(5, 0, 0), (0, 0, {
                'approver_type': 'direct_manager',
                'sequence': 10,
            })],
        })

    def _create_request(self, **kwargs):
        vals = {
            'employee_id': self.employee.id,
            'request_type_id': self.request_type_ot.id,
        }
        vals.update(kwargs)
        return self.env['hr.request'].create(vals)

    def test_request_sequence_on_create(self):
        req = self._create_request()
        self.assertNotEqual(req.name, 'Mới')
        self.assertTrue(req.name)

    def test_submit_creates_approval_records(self):
        req = self._create_request()
        req.action_submit()
        self.assertEqual(req.state, 'submitted')
        self.assertTrue(req.approval_ids)
        self.assertEqual(req.approval_ids[0].approver_id, self.manager_user)
        self.assertEqual(req.approval_ids[0].status, 'pending')

    def test_approve_workflow(self):
        req = self._create_request()
        req.action_submit()
        req.with_user(self.manager_user).action_approve()
        self.assertEqual(req.state, 'approved')
        approval = req.approval_ids[0]
        self.assertEqual(approval.status, 'approved')
        self.assertTrue(approval.approved_date)

    def test_refuse_workflow(self):
        req = self._create_request()
        req.action_submit()
        req.with_user(self.manager_user).action_refuse()
        self.assertEqual(req.state, 'refused')

    def test_cancel_draft(self):
        req = self._create_request()
        req.action_cancel()
        self.assertEqual(req.state, 'cancelled')

    def test_cancel_approved_raises(self):
        req = self._create_request()
        req.action_submit()
        req.with_user(self.manager_user).action_approve()
        with self.assertRaises(UserError):
            req.action_cancel()

    def test_reset_to_draft(self):
        req = self._create_request()
        req.action_submit()
        req.action_draft()
        self.assertEqual(req.state, 'draft')
        self.assertFalse(req.approval_ids)

    def test_approve_without_permission_raises(self):
        other_user = self.env['res.users'].create({
            'name': 'Other User',
            'login': 'other_user_req',
            'groups_id': [(4, self.env.ref('hr.group_hr_user').id)],
        })
        req = self._create_request()
        req.action_submit()
        with self.assertRaises(UserError):
            req.with_user(other_user).action_approve()

    def test_frequency_limit(self):
        self.request_type_ot.write({'frequency_limit': 1})
        req1 = self._create_request()
        req1.action_submit()

        req2 = self._create_request()
        with self.assertRaises(ValidationError):
            req2.action_submit()

        self.request_type_ot.write({'frequency_limit': 0})

    def test_duration_computation(self):
        from datetime import datetime
        req = self._create_request(
            date_from=datetime(2025, 1, 10, 8, 0, 0),
            date_to=datetime(2025, 1, 10, 16, 0, 0),
        )
        self.assertAlmostEqual(req.duration_hours, 8.0, places=1)
        self.assertAlmostEqual(req.duration_days, 1.0, places=1)
