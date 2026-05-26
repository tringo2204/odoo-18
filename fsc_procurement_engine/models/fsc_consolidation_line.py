import logging
from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class FscConsolidationLine(models.Model):
    _inherit = 'fsc.consolidation.line'

    decision_ids = fields.One2many(
        'fsc.make.buy.decision', 'consolidation_line_id',
        string='Make-vs-Buy Decisions',
    )

    def action_generate_procurement(self):
        """Evaluate make-vs-buy and generate the corresponding PO / MO.

        Acts on lines in 'open' state only. Lines outside that state are silently
        skipped so this action can safely be called on any selection.
        """
        eligible = self.filtered(lambda l: l.state == 'open')
        if not eligible:
            return False

        # Group by company so PO grouping never crosses companies.
        by_company = defaultdict(list)
        for line in eligible:
            by_company[line.company_id].append(line)

        for company, lines in by_company.items():
            buy_lines_by_vendor = defaultdict(list)
            for line in lines:
                decision_vals = line._fsc_evaluate_make_buy()
                decision = self.env['fsc.make.buy.decision'].create(decision_vals)
                if decision.decision == 'make':
                    line._fsc_generate_mo(decision)
                else:
                    vendor = decision.chosen_vendor_id or line._fsc_pick_vendor()
                    if not vendor:
                        raise UserError(_(
                            'No vendor configured for product %s. '
                            'Add a vendor on the product form before generating the RFQ.',
                            line.product_id.display_name,
                        ))
                    decision.chosen_vendor_id = vendor
                    buy_lines_by_vendor[vendor].append((line, decision))

            # Create one PO per (vendor, company) pair, attach all eligible lines.
            for vendor, line_decisions in buy_lines_by_vendor.items():
                self._fsc_create_or_update_po(company, vendor, line_decisions)

        return True

    def _fsc_evaluate_make_buy(self):
        """Return vals dict for an fsc.make.buy.decision record.

        Sprint 3 scope: buy by default. Make path activates only when the product
        is flagged as internal supplier. Capacity and cost_make computation are
        placeholders to be filled by the manufacturing planning module.
        """
        self.ensure_one()
        product = self.product_id
        is_internal = product.product_tmpl_id.fsc_is_internal_supplier
        cost_buy = self._fsc_estimate_buy_cost()
        cost_make = self._fsc_estimate_make_cost() if is_internal else 0.0
        capacity = is_internal  # placeholder; real check belongs to MRP planning

        if is_internal and capacity and cost_make and cost_make < cost_buy:
            decision = 'make'
            reason = _('Internal capacity available, make %.2f < buy %.2f') % (cost_make, cost_buy)
        else:
            decision = 'buy'
            if not is_internal:
                reason = _('Product is not flagged as internal supplier')
            elif not capacity:
                reason = _('No internal capacity available')
            else:
                reason = _('Buy cheaper or make cost not yet available (make=%.2f buy=%.2f)') % (cost_make, cost_buy)

        return {
            'consolidation_line_id': self.id,
            'product_id': product.id,
            'qty': self.total_qty,
            'cost_make': cost_make,
            'cost_buy': cost_buy,
            'capacity_available': capacity,
            'decision': decision,
            'decision_reason': reason,
        }

    def _fsc_estimate_buy_cost(self):
        """Cost = price_unit (in product UoM) × total_qty from best seller."""
        self.ensure_one()
        seller = self._fsc_pick_seller()
        if not seller:
            return 0.0
        # supplierinfo.price is in seller's UoM; convert to line UoM.
        if seller.product_uom and seller.product_uom != self.uom_id:
            qty_in_seller_uom = self.uom_id._compute_quantity(self.total_qty, seller.product_uom)
            return seller.price * qty_in_seller_uom
        return seller.price * self.total_qty

    def _fsc_estimate_make_cost(self):
        """Placeholder; the costing engine will replace this with a BOM-based estimate."""
        self.ensure_one()
        # Use the standard product cost as a coarse proxy.
        return (self.product_id.standard_price or 0.0) * self.total_qty

    def _fsc_pick_seller(self):
        """Return the best supplierinfo for this line's product + qty."""
        self.ensure_one()
        return self.product_id._select_seller(
            quantity=self.total_qty,
            uom_id=self.uom_id,
            date=fields.Date.context_today(self),
        )

    def _fsc_pick_vendor(self):
        """Return the vendor partner from the best supplierinfo."""
        seller = self._fsc_pick_seller()
        return seller.partner_id if seller else self.env['res.partner']

    @api.model
    def _fsc_create_or_update_po(self, company, vendor, line_decisions):
        """Find a draft PO for (company, vendor) or create one, then add lines."""
        PO = self.env['purchase.order']
        existing_po = PO.search([
            ('partner_id', '=', vendor.id),
            ('company_id', '=', company.id),
            ('state', '=', 'draft'),
        ], limit=1, order='id desc')

        if existing_po:
            po = existing_po
            origins = set(filter(None, (po.origin or '').split(', ')))
        else:
            po = PO.create({
                'partner_id': vendor.id,
                'company_id': company.id,
                'date_order': fields.Datetime.now(),
                'origin': '',
            })
            origins = set()

        POL = self.env['purchase.order.line']
        for line, decision in line_decisions:
            seller = line._fsc_pick_seller()
            price_unit = seller.price if seller else 0.0
            line_uom = line.uom_id
            # If supplier uses a different UoM, convert qty and use seller UoM.
            qty = line.total_qty
            if seller and seller.product_uom and seller.product_uom != line_uom:
                qty = line_uom._compute_quantity(qty, seller.product_uom)
                line_uom = seller.product_uom

            POL.create({
                'order_id': po.id,
                'product_id': line.product_id.id,
                'name': line.product_id.display_name,
                'product_qty': qty,
                'product_uom': line_uom.id,
                'price_unit': price_unit,
                'date_planned': line.required_date,
            })
            line.write({
                'state': 'rfq_created',
                'purchase_order_id': po.id,
            })
            origins.add(line.name)

        po.write({'origin': ', '.join(sorted(origins))})
        return po

    def _fsc_generate_mo(self, decision):
        """Create a manufacturing order for this line. Requires a BOM."""
        self.ensure_one()
        BOM = self.env['mrp.bom']
        bom = BOM._bom_find(
            products=self.product_id,
            company_id=self.company_id.id,
        ).get(self.product_id)
        if not bom:
            raise UserError(_(
                'No BOM found for %s; cannot create a manufacturing order. '
                'Either configure a BOM or set the product to buy-only.',
                self.product_id.display_name,
            ))
        mo = self.env['mrp.production'].create({
            'product_id': self.product_id.id,
            'product_qty': self.total_qty,
            'product_uom_id': self.uom_id.id,
            'bom_id': bom.id,
            'date_start': self.required_date,
            'company_id': self.company_id.id,
            'origin': self.name,
        })
        self.write({
            'state': 'mo_created',
            'production_id': mo.id,
        })
        return mo

    @api.model
    def _cron_process_open_lines(self):
        """Pick up all 'open' lines and generate procurement.

        Errors per-line are caught and logged so one bad line doesn't block others.
        """
        open_lines = self.search([('state', '=', 'open')])
        success = 0
        for line in open_lines:
            try:
                line.action_generate_procurement()
                success += 1
            except UserError as e:
                _logger.warning('FSC procurement: line %s skipped: %s', line.name, e)
            except Exception:
                _logger.exception('FSC procurement: unexpected error on line %s', line.name)
        return success
