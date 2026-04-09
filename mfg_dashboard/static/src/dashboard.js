/** @odoo-module */

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class MfgDashboard extends Component {
    static template = "mfg_dashboard.Dashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            data: null,
            loading: true,
            lastRefresh: null,
        });

        onWillStart(() => this.loadData());

        onMounted(() => {
            this._refreshInterval = setInterval(() => this.loadData(), 5 * 60 * 1000);
        });
    }

    async loadData() {
        this.state.loading = true;
        try {
            const data = await this.orm.call("mfg.dashboard", "get_dashboard_data", []);
            this.state.data = data;
            this.state.lastRefresh = new Date().toLocaleTimeString();
        } finally {
            this.state.loading = false;
        }
    }

    openList(model, domain, name) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: name,
            res_model: model,
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: domain,
        });
    }

    openProduction(state) {
        const domain = state ? [["state", "=", state]] : [];
        const labels = {
            draft: "Draft Orders", confirmed: "Confirmed Orders",
            progress: "In Progress", done: "Completed This Month",
            late: "Late Orders",
        };
        if (state === "late") {
            this.openList("mrp.production",
                [["state", "in", ["confirmed", "progress", "to_close"]], ["date_deadline", "<", new Date().toISOString()], ["date_deadline", "!=", false]],
                "Late Production Orders");
        } else {
            this.openList("mrp.production", domain, labels[state] || "Production Orders");
        }
    }

    openWorkorder(state) {
        const labels = { ready: "Ready Work Orders", progress: "In Progress", pending: "Pending", waiting: "Waiting" };
        this.openList("mrp.workorder", state ? [["state", "=", state]] : [], labels[state] || "Work Orders");
    }

    openQuality(state) {
        const labels = { none: "Pending Checks", fail: "Failed Checks", pass: "Passed This Month" };
        this.openList("quality.check", state ? [["quality_state", "=", state]] : [], labels[state] || "Quality Checks");
    }

    openAlerts(critical) {
        const domain = critical
            ? [["stage_id.done", "=", false], ["priority", "=", "1"]]
            : [["stage_id.done", "=", false]];
        this.openList("quality.alert", domain, critical ? "Critical Alerts" : "Open Alerts");
    }

    openMaintenance(urgent) {
        const domain = urgent
            ? [["stage_id.done", "=", false], ["priority", "=", "3"], ["archive", "=", false]]
            : [["stage_id.done", "=", false], ["archive", "=", false]];
        this.openList("maintenance.request", domain, urgent ? "Urgent Requests" : "Open Requests");
    }

    openECO(state) {
        const labels = { confirmed: "New ECOs", progress: "ECOs In Progress", done: "Completed This Month" };
        this.openList("mrp.eco", state ? [["state", "=", state]] : [], labels[state] || "ECOs");
    }
}

registry.category("actions").add("mfg_dashboard", MfgDashboard);
