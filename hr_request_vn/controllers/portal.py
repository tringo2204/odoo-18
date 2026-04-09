from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class HrRequestPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'request_count' in counters:
            employee = request.env.user.employee_id
            if employee:
                values['request_count'] = request.env['hr.request'].search_count([
                    ('employee_id', '=', employee.id),
                ])
            else:
                values['request_count'] = 0
        return values

    @http.route(['/my/requests', '/my/requests/page/<int:page>'],
                type='http', auth='user', website=True)
    def portal_my_requests(self, page=1, sortby=None, **kw):
        employee = request.env.user.employee_id
        if not employee:
            return request.redirect('/my')

        domain = [('employee_id', '=', employee.id)]
        HrRequest = request.env['hr.request']
        request_count = HrRequest.search_count(domain)

        pager = portal_pager(
            url='/my/requests',
            total=request_count,
            page=page,
            step=10,
        )

        requests = HrRequest.search(
            domain, order='create_date desc',
            limit=10, offset=pager['offset'],
        )

        values = {
            'requests': requests,
            'pager': pager,
            'page_name': 'requests',
            'default_url': '/my/requests',
        }
        return request.render('hr_request_vn.portal_my_requests', values)

    @http.route(['/my/requests/<int:request_id>'],
                type='http', auth='user', website=True)
    def portal_my_request_detail(self, request_id, **kw):
        employee = request.env.user.employee_id
        hr_request = request.env['hr.request'].browse(request_id)

        if not hr_request.exists() or hr_request.employee_id != employee:
            return request.redirect('/my/requests')

        values = {
            'hr_request': hr_request,
            'page_name': 'request_detail',
        }
        return request.render('hr_request_vn.portal_my_request_detail', values)
