from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    fsc_dual_confirm_required = fields.Boolean(
        related='picking_type_id.fsc_dual_confirm', store=True,
    )
    fsc_warehouse_confirmed = fields.Boolean(string='WH Confirmed', readonly=True,
                                             copy=False, tracking=True)
    fsc_kitchen_confirmed = fields.Boolean(string='Kitchen Confirmed', readonly=True,
                                           copy=False, tracking=True)
    fsc_warehouse_confirmed_by = fields.Many2one('res.users', string='WH Confirmed By',
                                                 readonly=True, copy=False)
    fsc_kitchen_confirmed_by = fields.Many2one('res.users', string='Kitchen Confirmed By',
                                               readonly=True, copy=False)
    fsc_warehouse_confirmed_at = fields.Datetime(string='WH Confirmed At',
                                                 readonly=True, copy=False)
    fsc_kitchen_confirmed_at = fields.Datetime(string='Kitchen Confirmed At',
                                               readonly=True, copy=False)
    fsc_transfer_discrepancy_ids = fields.One2many(
        'fsc.transfer.discrepancy', 'picking_id', string='Transfer Discrepancies',
    )
    fsc_discrepancy_count = fields.Integer(
        compute='_compute_fsc_discrepancy_count',
    )

    def _compute_fsc_discrepancy_count(self):
        for picking in self:
            picking.fsc_discrepancy_count = len(picking.fsc_transfer_discrepancy_ids)

    def action_fsc_warehouse_confirm(self):
        for picking in self:
            if not picking.fsc_dual_confirm_required:
                raise UserError(_('This picking does not require FSC dual confirmation.'))
            if picking.fsc_warehouse_confirmed:
                raise UserError(_(
                    'Warehouse confirmation is already recorded for %s.', picking.name,
                ))
            # Snapshot the dispatched quantities at confirm time.
            for move in picking.move_ids:
                move.fsc_warehouse_qty = move.quantity or 0.0
            picking.write({
                'fsc_warehouse_confirmed': True,
                'fsc_warehouse_confirmed_by': self.env.uid,
                'fsc_warehouse_confirmed_at': fields.Datetime.now(),
            })
            picking.message_post(body=_(
                'Warehouse dispatch confirmed by %s.', self.env.user.name,
            ))
        return True

    def action_fsc_kitchen_confirm(self):
        for picking in self:
            if not picking.fsc_dual_confirm_required:
                raise UserError(_('This picking does not require FSC dual confirmation.'))
            if not picking.fsc_warehouse_confirmed:
                raise UserError(_(
                    'Warehouse must confirm dispatch on %s before kitchen receipt.',
                    picking.name,
                ))
            if picking.fsc_kitchen_confirmed:
                raise UserError(_(
                    'Kitchen confirmation is already recorded for %s.', picking.name,
                ))
            picking._fsc_snapshot_kitchen_and_record_discrepancies()
            picking.write({
                'fsc_kitchen_confirmed': True,
                'fsc_kitchen_confirmed_by': self.env.uid,
                'fsc_kitchen_confirmed_at': fields.Datetime.now(),
            })
            picking.message_post(body=_(
                'Kitchen receipt confirmed by %s.', self.env.user.name,
            ))
        return True

    def _fsc_snapshot_kitchen_and_record_discrepancies(self):
        self.ensure_one()
        Discrepancy = self.env['fsc.transfer.discrepancy']
        for move in self.move_ids:
            kitchen_qty = move.quantity or 0.0
            move.fsc_kitchen_qty = kitchen_qty
            wh_qty = move.fsc_warehouse_qty or 0.0
            rounding = move.product_uom.rounding if move.product_uom else 0.0001
            if float_compare(wh_qty, kitchen_qty, precision_rounding=rounding) != 0:
                Discrepancy.create({
                    'picking_id': self.id,
                    'product_id': move.product_id.id,
                    'warehouse_qty': wh_qty,
                    'kitchen_qty': kitchen_qty,
                    'warehouse_confirmed_by': self.fsc_warehouse_confirmed_by.id,
                    'kitchen_confirmed_by': self.env.uid,
                    'state': 'open',
                })

    def button_validate(self):
        for picking in self:
            if picking.fsc_dual_confirm_required and not (
                picking.fsc_warehouse_confirmed and picking.fsc_kitchen_confirmed
            ):
                raise UserError(_(
                    'Transfer %s requires both warehouse and kitchen confirmation '
                    'before validation. Warehouse confirmed: %s. Kitchen confirmed: %s.',
                    picking.name,
                    picking.fsc_warehouse_confirmed and 'yes' or 'no',
                    picking.fsc_kitchen_confirmed and 'yes' or 'no',
                ))
        return super().button_validate()

    def action_open_fsc_discrepancies(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Transfer Discrepancies'),
            'res_model': 'fsc.transfer.discrepancy',
            'view_mode': 'list,form',
            'domain': [('picking_id', '=', self.id)],
        }
