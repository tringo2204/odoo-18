import logging
from collections import defaultdict
from datetime import timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class StockRule(models.Model):
    _inherit = 'stock.rule'

    fsc_consolidate = fields.Boolean(
        string='Push to FSC Consolidation',
        help='When set, demand routed through this buy rule is intercepted and '
             'pushed into the FSC demand consolidation engine instead of creating '
             'a purchase order directly. The procurement engine then groups demand '
             'across kitchens and generates RFQs in batches.',
    )

    @api.model
    def _run_buy(self, procurements):
        to_consolidate = []
        to_pass = []
        for proc, rule in procurements:
            if rule.fsc_consolidate and not self._fsc_is_urgent(proc):
                to_consolidate.append((proc, rule))
            else:
                to_pass.append((proc, rule))

        if to_consolidate:
            self._fsc_push_to_consolidation(to_consolidate)

        if to_pass:
            return super()._run_buy(to_pass)
        return True

    @api.model
    def _fsc_is_urgent(self, procurement):
        # stock.move.priority: '0' Normal, '1' Urgent (Odoo convention).
        return str(procurement.values.get('priority') or '0') == '1'

    @api.model
    def _fsc_push_to_consolidation(self, procurements):
        Line = self.env['fsc.consolidation.line'].sudo()

        # Group by company first so consolidation never crosses companies.
        by_company = defaultdict(list)
        for proc, rule in procurements:
            company = rule.company_id or proc.company_id or self.env.company
            by_company[company].append((proc, rule))

        for company, procs in by_company.items():
            for proc, rule in procs:
                date_planned = proc.values.get('date_planned') or fields.Datetime.now()
                if isinstance(date_planned, str):
                    date_planned = fields.Datetime.from_string(date_planned)
                # Match-by-day: same product + uom + same day = merge.
                day_start = date_planned.replace(hour=0, minute=0, second=0, microsecond=0)
                day_end = day_start + timedelta(days=1)

                existing = Line.search([
                    ('company_id', '=', company.id),
                    ('product_id', '=', proc.product_id.id),
                    ('uom_id', '=', proc.product_uom.id),
                    ('state', '=', 'draft'),
                    ('required_date', '>=', day_start),
                    ('required_date', '<', day_end),
                ], limit=1, order='required_date asc, id asc')

                move_dest = proc.values.get('move_dest_ids') or self.env['stock.move']

                if existing:
                    self._fsc_merge_into_line(existing, proc, move_dest)
                else:
                    Line.create(self._fsc_prepare_line_vals(company, proc, move_dest))

        return True

    @api.model
    def _fsc_merge_into_line(self, line, procurement, move_dest):
        line.total_qty += procurement.product_qty
        if procurement.origin:
            existing_origins = set((line.origin or '').split(', ')) - {''}
            existing_origins.add(procurement.origin)
            line.origin = ', '.join(sorted(existing_origins))
        if procurement.location_id:
            line.source_location_ids = [(4, procurement.location_id.id)]
        if move_dest:
            line.demand_move_ids = [(4, m.id) for m in move_dest]
        _logger.info(
            'FSC consolidation: merged %.4f %s of %s into line %s (new total %.4f)',
            procurement.product_qty, procurement.product_uom.name,
            procurement.product_id.display_name, line.name, line.total_qty,
        )

    @api.model
    def _fsc_prepare_line_vals(self, company, procurement, move_dest):
        date_planned = procurement.values.get('date_planned') or fields.Datetime.now()
        if isinstance(date_planned, str):
            date_planned = fields.Datetime.from_string(date_planned)
        vals = {
            'company_id': company.id,
            'product_id': procurement.product_id.id,
            'uom_id': procurement.product_uom.id,
            'total_qty': procurement.product_qty,
            'required_date': date_planned,
            'origin': procurement.origin or False,
            'state': 'draft',
            'urgency': 'normal',
        }
        if procurement.location_id:
            vals['source_location_ids'] = [(6, 0, [procurement.location_id.id])]
        if move_dest:
            vals['demand_move_ids'] = [(6, 0, move_dest.ids)]
        return vals
