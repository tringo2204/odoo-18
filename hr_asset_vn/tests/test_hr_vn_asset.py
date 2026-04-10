from odoo.tests import TransactionCase, tagged
from odoo.exceptions import UserError


@tagged('post_install', '-at_install')
class TestHrVnAsset(TransactionCase):
    """Test asset allocation and return workflows."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.category = cls.env['hr.vn.asset.category'].create({
            'name': 'Laptop',
            'depreciation_years': 3,
        })
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Asset Test Employee',
        })

    def _create_asset(self, **kwargs):
        vals = {
            'name': 'Test Laptop',
            'category_id': self.category.id,
            'purchase_value': 30_000_000,
            'purchase_date': '2024-01-01',
        }
        vals.update(kwargs)
        return self.env['hr.vn.asset'].create(vals)

    def test_asset_default_state(self):
        asset = self._create_asset()
        self.assertEqual(asset.state, 'available')

    def test_asset_sequence_code(self):
        asset = self._create_asset()
        self.assertNotEqual(asset.code, 'Mới')

    def test_depreciation_computation(self):
        asset = self._create_asset()
        self.assertGreater(asset.monthly_depreciation, 0)
        self.assertTrue(asset.residual_value <= asset.purchase_value)

    def test_allocate_asset(self):
        asset = self._create_asset()
        self.env['hr.vn.asset.allocation'].create({
            'asset_id': asset.id,
            'employee_id': self.employee.id,
            'allocation_type': 'allocate',
        })
        self.assertEqual(asset.state, 'allocated')
        self.assertEqual(asset.current_employee_id, self.employee)

    def test_return_asset_good(self):
        asset = self._create_asset()
        self.env['hr.vn.asset.allocation'].create({
            'asset_id': asset.id,
            'employee_id': self.employee.id,
            'allocation_type': 'allocate',
        })
        self.env['hr.vn.asset.allocation'].create({
            'asset_id': asset.id,
            'employee_id': self.employee.id,
            'allocation_type': 'return',
            'condition_on_return': 'good',
        })
        self.assertEqual(asset.state, 'available')
        self.assertFalse(asset.current_employee_id)

    def test_return_asset_damaged(self):
        asset = self._create_asset()
        self.env['hr.vn.asset.allocation'].create({
            'asset_id': asset.id,
            'employee_id': self.employee.id,
            'allocation_type': 'allocate',
        })
        self.env['hr.vn.asset.allocation'].create({
            'asset_id': asset.id,
            'employee_id': self.employee.id,
            'allocation_type': 'return',
            'condition_on_return': 'damaged',
        })
        self.assertEqual(asset.state, 'maintenance')

    def test_return_asset_lost(self):
        asset = self._create_asset()
        self.env['hr.vn.asset.allocation'].create({
            'asset_id': asset.id,
            'employee_id': self.employee.id,
            'allocation_type': 'allocate',
        })
        self.env['hr.vn.asset.allocation'].create({
            'asset_id': asset.id,
            'employee_id': self.employee.id,
            'allocation_type': 'return',
            'condition_on_return': 'lost',
        })
        self.assertEqual(asset.state, 'disposed')

    def test_allocate_non_available_raises(self):
        asset = self._create_asset()
        asset.action_dispose()
        with self.assertRaises(UserError):
            self.env['hr.vn.asset.allocation'].create({
                'asset_id': asset.id,
                'employee_id': self.employee.id,
                'allocation_type': 'allocate',
            })

    def test_action_dispose(self):
        asset = self._create_asset()
        asset.action_dispose()
        self.assertEqual(asset.state, 'disposed')

    def test_action_maintenance(self):
        asset = self._create_asset()
        asset.action_maintenance()
        self.assertEqual(asset.state, 'maintenance')

    def test_action_available(self):
        asset = self._create_asset()
        asset.action_maintenance()
        asset.action_available()
        self.assertEqual(asset.state, 'available')
        self.assertFalse(asset.current_employee_id)

    def test_allocation_count(self):
        asset = self._create_asset()
        self.assertEqual(asset.allocation_count, 0)
        self.env['hr.vn.asset.allocation'].create({
            'asset_id': asset.id,
            'employee_id': self.employee.id,
            'allocation_type': 'allocate',
        })
        self.assertEqual(asset.allocation_count, 1)
