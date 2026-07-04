# -*- coding: utf-8 -*-
"""Master synthetic data generator for the NovaCart AI Operations Copilot.

This script produces the full set of CSV, Markdown, and JSON files that the
agent and its evaluation harness rely on.  Every dataset is deterministic
(seeded with ``random.seed(42)``) so that runs are reproducible.

Output layout::

    data/
    ├── daily_metrics.csv              # 180 days of company-level KPIs
    ├── daily_category_metrics.csv     # Per-category breakdown
    ├── daily_warehouse_metrics.csv    # Per-warehouse breakdown
    ├── daily_channel_metrics.csv      # Per-channel breakdown
    ├── product_categories.csv         # Static product catalogue
    ├── docs/
    │   ├── 01_company_overview.md …   # Knowledge-base handbook (10 sections)
    │   ├── week_01_… .md …            # Weekly ops reports (16 weeks)
    │   ├── incident_001_… .md …       # Incident reports (5 incidents)
    │   ├── sop_001_… .md …            # Standard operating procedures (4 SOPs)
    │   └── escalation_logs.json       # Structured escalation history

Usage
-----
    python data/generate_data.py

Idempotent — safe to run multiple times (overwrites files in place).
"""

import csv
import json
import os
import random
from datetime import datetime, timedelta

# Deterministic seed – change to 42 for identical output every run.
random.seed(42)

# Root output directory is ``data/`` (where this script lives).
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(OUTPUT_DIR, "docs")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def daterange(start: str, days: int):
    """Yield ``YYYY-MM-DD`` strings from *start* for *days* days."""
    start_dt = datetime.strptime(start, "%Y-%m-%d")
    for i in range(days):
        yield (start_dt + timedelta(days=i)).strftime("%Y-%m-%d")


def write_md(filename: str, content: str):
    """Write a Markdown file to the ``docs/`` subdirectory."""
    with open(os.path.join(DOCS_DIR, filename), "w", encoding="utf-8") as f:
        f.write(content)


def write_json(filename: str, data):
    """Write JSON to the ``docs/`` subdirectory (indented for readability)."""
    with open(os.path.join(DOCS_DIR, filename), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def noisy(value: float, pct: float = 0.05) -> float:
    """Add ±*pct* % random noise to *value* and round to 2 decimals.

    Used to make generated metrics look more realistic.
    """
    return round(value * (1 + random.uniform(-pct, pct)), 2)


# Short-hand constants used in Markdown tables (keeps lines shorter).
LE = "<="
GE = ">="
EM = "--"

# ---------------------------------------------------------------------------
# Handbook (knowledge-base) content
# ---------------------------------------------------------------------------

HANDBOOK_SECTIONS = {
    "01_company_overview.md": (
        "# NovaCart - Company Overview\n\n"
        "## Mission\n"
        "NovaCart delivers a seamless online shopping experience with reliable fulfillment and exceptional customer satisfaction.\n\n"
        "## Company Profile\n"
        "- Founded: 2019\n"
        "- Headquarters: Austin, TX\n"
        "- Employees: ~520\n"
        "- Fulfillment Centers: 3 (Austin-TX, Newark-NJ, Reno-NV)\n"
        "- Monthly Order Volume: 50,000-200,000\n"
        "- Active SKUs: ~25,000\n"
        "- Operating Regions: USA and Canada\n\n"
        "## Leadership\n"
        "- CEO: Maria Torres\n"
        "- COO: James Chen\n"
        "- VP Engineering: Priya Sharma\n"
        "- VP Operations: Michael Okonkwo\n"
        "- VP Customer Experience: Lisa Park\n"
        "- Director of Fulfillment: David Kim\n"
        "- Director of Data & Analytics: Sarah Mitchell\n\n"
        "## Org Structure\n"
        "Operations falls under the COO and includes: Fulfillment, Inventory Management, "
        "Quality Assurance, Supply Chain, and Business Operations Analysis.\n"
    ),
    "02_kpi_definitions.md": (
        "# KPI Definitions\n\n"
        "| KPI | Formula | Data Source | Refresh |\n"
        "|---|---|---|---|\n"
        "| Order Volume | Count of completed orders | Order System | Daily |\n"
        "| Avg Fulfillment Time (hrs) | Avg(dispatch_time - order_time) per day | Fulfillment System | Daily |\n"
        "| Fulfillment Time p95 (hrs) | 95th percentile of fulfillment times | Fulfillment System | Daily |\n"
        "| Return Rate (%) | Returned Orders / Delivered Orders x 100 | Returns System | Daily |\n"
        "| Return Volume | Count of returned orders | Returns System | Daily |\n"
        "| Avg Wait Time (min) | Avg time in queue before agent pickup | Contact Center | Daily |\n"
        "| CSAT Score | Avg survey score (1-5) | Survey System | Daily |\n"
        "| Revenue ($) | Total order value after discounts | Billing System | Daily |\n"
        "| Units Shipped | Total item units dispatched | Fulfillment System | Daily |\n"
        "| Shipping Cost ($) | Total carrier costs | Carrier Billing | Daily |\n"
        "| Inventory Accuracy (%) | (1 - |variance| / book qty) x 100 | WMS | Weekly |\n"
        "| On-Time Delivery (%) | Orders delivered by promised date | Carrier Data | Daily |\n"
        "| Cart Abandonment (%) | Abandoned / Started x 100 | Analytics Platform | Daily |\n"
        "| CSAT by Channel | CSAT segmented by web/mobile/phone | Survey System | Daily |\n"
        "| AOV ($) | Revenue / Order Volume | Billing System | Daily |\n"
    ),
    "03_sla_targets.md": (
        "# SLA Targets\n\n"
        "| Metric | Target | Critical Threshold |\n"
        "|---|---|---|\n"
        "| Avg Fulfillment Time | " + LE + " 24 hours | > 36 hours |\n"
        "| Fulfillment Time p95 | " + LE + " 48 hours | > 60 hours |\n"
        "| Return Rate | " + LE + " 8% | > 12% |\n"
        "| CSAT Score | " + GE + " 4.2 / 5.0 | < 3.8 |\n"
        "| Avg Wait Time | " + LE + " 2 minutes | > 4 minutes |\n"
        "| Inventory Accuracy | " + GE + " 98% | < 95% |\n"
        "| On-Time Delivery | " + GE + " 95% | < 90% |\n"
        "| Cart Abandonment | " + LE + " 70% | > 80% |\n\n"
        "## Escalation Protocol\n"
        "When a KPI breaches its critical threshold for 2 consecutive days, a Tier-2 escalation "
        "is triggered. For 3+ consecutive days, a Tier-3 escalation with COO notification is required.\n"
    ),
    "04_escalation_procedures.md": (
        "# Escalation Procedures\n\n"
        "## Tier Definitions\n"
        "- **Tier 1 (Team Lead):** KPI breach < 2 days, single incident\n"
        "- **Tier 2 (Operations Manager):** KPI breach 2+ consecutive days, or incident with moderate impact\n"
        "- **Tier 3 (COO / VP Ops):** KPI breach 3+ days, critical impact, revenue impact > $50K\n\n"
        "## When to Escalate\n"
        "1. Any critical threshold breach lasting 2+ days\n"
        "2. Any safety or compliance incident\n"
        "3. Customer-facing outage > 30 minutes\n"
        "4. Inventory variance > 5% in any category\n"
        "5. Supplier quality failure affecting > 1,000 units\n\n"
        "## Escalation Process\n"
        "1. Incident reporter fills the escalation template\n"
        "2. Tier-1 lead triages within 30 minutes\n"
        "3. If unresolved in 2 hours -> Tier-2\n"
        "4. If unresolved in 6 hours -> Tier-3 (with COO notification)\n\n"
        "## Contact Directory\n"
        "- Tier-1 Duty Lead: ops-lead@novacart.com\n"
        "- Tier-2 Ops Manager: ops-mgr@novacart.com\n"
        "- Tier-3 COO: coo@novacart.com\n"
        "- Emergency (outage): oncall@novacart.com\n"
    ),
    "05_reporting_calendar.md": (
        "# Reporting Calendar\n\n"
        "| Frequency | Meeting | Attendees | Data Required |\n"
        "|---|---|---|---|\n"
        "| Daily | Morning Ops Standup (9:00 AM CT) | Ops team | Previous day KPIs, incidents, anomalies |\n"
        "| Weekly | Weekly Ops Review (Monday 10:00 AM) | Ops + Product | Weekly trends, top issues, action items |\n"
        "| Monthly | Monthly Business Review (1st Wed) | Leadership | Full KPI deck, financials, strategic |\n"
        "| Quarterly | Quarterly Ops Planning | All departments | Deep dives, initiatives, resource planning |\n\n"
        "## Daily Standup Format\n"
        "1. KPI snapshot (5 KPIs: volume, fulfillment, returns, wait time, CSAT)\n"
        "2. Anomalies from last 24 hours\n"
        "3. Active escalations\n"
        "4. Priorities for today\n"
    ),
    "06_incident_response.md": (
        "# Incident Response\n\n"
        "## Severity Classification\n"
        "| Severity | Definition | Response SLA | Examples |\n"
        "|---|---|---|---|\n"
        "| Critical | Revenue impact > $50K or full outage | 15 min | Warehouse fire, payment system down |\n"
        "| High | Revenue impact $10K-$50K or partial outage | 30 min | Conveyor failure, gateway timeout |\n"
        "| Medium | Impact < $10K, no customer-facing effect | 2 hours | Inventory discrepancy, minor delays |\n"
        "| Low | No revenue impact, cosmetic/nuisance | Next business day | Report lag, minor data discrepancy |\n\n"
        "## Post-Mortem Requirements\n"
        "- Critical & High incidents require a post-mortem within 5 business days\n"
        "- Must include: timeline, root cause, impact, action items, owner\n"
        "- All post-mortems are stored in the Incident Log repository\n"
    ),
    "07_data_dictionary.md": (
        "# Data Dictionary\n\n"
        "| Field | Type | Example | Description |\n"
        "|---|---|---|---|\n"
        "| date | date | 2026-06-15 | Business date |\n"
        "| order_volume | int | 4250 | Completed orders |\n"
        "| fulfillment_time_avg | float | 18.5 | Avg hours from order to dispatch |\n"
        "| fulfillment_time_p95 | float | 42.3 | 95th percentile fulfillment hours |\n"
        "| return_rate | float | 7.2 | % of orders returned |\n"
        "| return_volume | int | 306 | Count of returned orders |\n"
        "| avg_wait_time_min | float | 1.8 | Avg minutes in support queue |\n"
        "| csat_score | float | 4.3 | Customer satisfaction (1-5) |\n"
        "| revenue | float | 425000.00 | Total daily revenue |\n"
        "| units_shipped | int | 6200 | Total units dispatched |\n"
        "| shipping_cost | float | 31000.00 | Daily carrier costs |\n"
        "| inventory_accuracy | float | 98.5 | % inventory accuracy |\n"
        "| category | string | Electronics | Product category |\n"
        "| warehouse | string | A | Fulfillment center ID |\n"
        "| channel | string | web | Order/support channel |\n"
    ),
    "08_compliance_policies.md": (
        "# Compliance Policies\n\n"
        "## Data Handling\n"
        "- PII (personally identifiable information) must never be stored in logs\n"
        "- Customer names, emails, addresses, and payment data must be masked in any output\n"
        "- Log retention: 90 days for operational logs, 7 years for financial records\n\n"
        "## Audit Trail\n"
        "- All modifications to KPI definitions or SLA thresholds must be logged with user ID and timestamp\n"
        "- Weekly compliance review checklists must be filed by EOD each Friday\n\n"
        "## Security\n"
        "- API keys and secrets must use environment variables or a secrets manager\n"
        "- No credentials in code, config files, or documentation\n"
        "- Access to operations data is read-only for analysts\n"
    ),
    "09_fulfillment_center_profiles.md": (
        "# Fulfillment Center Profiles\n\n"
        "## Warehouse A " + EM + " Austin, TX\n"
        "- Size: 250,000 sq ft\n"
        "- Headcount: 180\n"
        "- Specialization: Electronics, Books, Beauty & Health\n"
        "- Current Status: Staffing shortage since Week 8 (15% below target)\n\n"
        "## Warehouse B " + EM + " Newark, NJ\n"
        "- Size: 300,000 sq ft\n"
        "- Headcount: 200\n"
        "- Specialization: Clothing, Home & Garden, Automotive\n"
        "- Current Status: Operating normally (conveyor failure incident on Jun 12 resolved)\n\n"
        "## Warehouse C " + EM + " Reno, NV\n"
        "- Size: 200,000 sq ft\n"
        "- Headcount: 150\n"
        "- Specialization: Sports & Outdoors, Toys & Games, Automotive\n"
        "- Current Status: Operating normally\n"
    ),
    "10_standard_operating_procedures.md": (
        "# Standard Operating Procedures\n\n"
        "## SOP-001: Fulfillment Delay Handling\n"
        "When fulfillment time exceeds 30 hours average for a day:\n"
        "1. Identify bottleneck (picking, packing, carrier pickup)\n"
        "2. Alert Warehouse Lead\n"
        "3. If > 36 hours -> trigger Tier-1 escalation\n"
        "4. Communicate updated ETA to affected customers\n"
        "5. Log root cause in incident tracker\n\n"
        "## SOP-002: Inventory Reconciliation\n"
        "Weekly cycle count process:\n"
        "1. Count 5% of SKUs in each category\n"
        "2. If variance > 2% -> recount immediately\n"
        "3. If variance > 5% -> full category recount + Tier-1 escalation\n"
        "4. Update WMS with corrected counts\n"
        "5. File reconciliation report by Friday COB\n\n"
        "## SOP-003: Returns Processing\n"
        "1. Inspect returned items within 48 hours of receipt\n"
        "2. Grade items (A: Like-new -> restock, B: Used -> discount, C: Damaged -> dispose)\n"
        "3. Update return reason codes in system\n"
        "4. If category return rate > 12% -> flag for quality review\n"
        "5. Process refund within 3 business days\n\n"
        "## SOP-004: Monthly Ops Reporting\n"
        "1. Compile daily KPIs into monthly summary by 3rd business day\n"
        "2. Compare actuals vs targets with variance analysis\n"
        "3. Identify top 3 issues and propose corrective actions\n"
        "4. Draft narrative report with trends and recommendations\n"
        "5. Submit to VP Operations by 5th business day\n"
    ),
}


# ---------------------------------------------------------------------------
# Daily metric generation
# ---------------------------------------------------------------------------


def generate_daily_metrics():
    """Generate four CSV files with 180 days of synthetic business data.

    Files created
    ~~~~~~~~~~~~~
    * ``daily_metrics.csv``           – 12 company-wide KPIs per day
    * ``daily_category_metrics.csv``  – per-category volume / returns / revenue / rating
    * ``daily_warehouse_metrics.csv`` – per-warehouse volume / fulfillment / headcount
    * ``daily_channel_metrics.csv`    – per-channel volume / wait time / CSAT

    Data characteristics
    ~~~~~~~~~~~~~~~~~~~~
    - **Seasonality**: volume peaks in Nov–Dec (×1.4), dips in summer (×0.85).
    - **Weekly pattern**: weekends get 10–30 % more orders.
    - **Trend**: base volume grows 15 % over the 180-day window.
    - **Known incidents** embedded in the data:
        * 2026-06-12 : Warehouse B conveyor failure (fulfillment ×2.5, volume ×0.7).
        * 2026-07-05 : Payment gateway outage (fulfillment ×1.3, volume ×0.85).
        * 2026-04-15–16 : Mobile app regression (fulfillment ×1.8, volume ×0.8).
    - **Warehouse A staffing shortage**: begins Week 8 (day 56) with fulfillment
      degrading linearly from that point.
    - **Electronics return spike**: 2026-03-22–28 (defective headphone batch).
    - **Mobile regression**: 2026-04-01–14 (increased wait times, lower CSAT).
    """
    rows = []
    categories = [
        "Electronics", "Clothing", "Home & Garden", "Books",
        "Sports & Outdoors", "Beauty & Health", "Toys & Games", "Automotive",
    ]
    warehouses = ["A", "B", "C"]
    channels = ["web", "mobile", "phone"]
    # Day-of-week multipliers for base volume (Mon=0 … Sun=6).
    weekly_volume_boost = {0: 1.0, 1: 0.9, 2: 0.95, 3: 1.0, 4: 1.05, 5: 1.3, 6: 1.1}

    for i, date in enumerate(daterange("2026-01-01", 180)):
        dt = datetime.strptime(date, "%Y-%m-%d")
        day_of_week = dt.weekday()
        month = dt.month

        # Factors that scale base volume.
        seasonal_factor = 1.4 if month in [11, 12] else (0.85 if month in [6, 7, 8] else 1.0)
        wd_boost = weekly_volume_boost[day_of_week]
        trend = 1.0 + (i / 180) * 0.15
        base_volume = 4000

        # Incident-day overrides for volume and fulfillment.
        if date == "2026-06-12":
            fulfillment_factor, volume_factor = 2.5, 0.7
        elif date == "2026-07-05":
            fulfillment_factor, volume_factor = 1.3, 0.85
        elif date in ["2026-04-15", "2026-04-16"]:
            fulfillment_factor, volume_factor = 1.8, 0.8
        else:
            fulfillment_factor, volume_factor = 1.0, 1.0

        order_volume = int(base_volume * seasonal_factor * wd_boost * trend * volume_factor)

        # Fulfillment base (hours).  Starts at 18.0; Warehouse A staffing
        # shortage causes a linear climb from day 56 onward.
        fulfillment_base = 18.0
        if i > 56:
            fulfillment_base += 4.0 * ((i - 56) / 124)

        if date == "2026-06-12":
            avg_fulfill = round(fulfillment_base * 2.5, 1)
        elif date in ["2026-04-15", "2026-04-16"]:
            avg_fulfill = round(fulfillment_base * 1.8, 1)
        else:
            avg_fulfill = round(fulfillment_base + random.uniform(-2, 2), 1)

        p95_fulfill = round(avg_fulfill * random.uniform(1.8, 2.5), 1)

        # Return rate: normally 5–9 %, spikes during headphone recall.
        return_rate = round(random.uniform(5.0, 9.0), 1)
        if "2026-03-22" <= date <= "2026-03-28":
            return_rate = round(random.uniform(11.0, 14.0), 1)
        elif "2026-03-29" <= date <= "2026-04-04":
            return_rate = round(random.uniform(8.0, 10.0), 1)
        return_volume = int(order_volume * return_rate / 100)

        # Wait time & CSAT (mobile regression affects Apr 1–14).
        wait_base = random.uniform(1.0, 2.5)
        if "2026-04-01" <= date <= "2026-04-14":
            wait_base = random.uniform(2.5, 4.5)
        csat = round(4.5 - (wait_base - 1.5) * 0.3 + random.uniform(-0.2, 0.2), 2)
        csat = max(3.0, min(5.0, csat))
        if "2026-04-01" <= date <= "2026-04-14":
            csat = round(csat - random.uniform(0.3, 0.6), 2)
            csat = max(3.0, csat)

        revenue = round(order_volume * random.uniform(80, 140), 2)
        units_shipped = int(order_volume * random.uniform(1.2, 2.0))
        shipping_cost = round(units_shipped * random.uniform(4.5, 7.5), 2)
        inventory_accuracy = 92.0 if date == "2026-08-01" else round(random.uniform(96.0, 99.5), 1)

        rows.append({
            "date": date, "order_volume": order_volume,
            "fulfillment_time_avg": avg_fulfill, "fulfillment_time_p95": p95_fulfill,
            "return_rate": return_rate, "return_volume": return_volume,
            "avg_wait_time_min": round(wait_base, 1), "csat_score": csat,
            "revenue": revenue, "units_shipped": units_shipped,
            "shipping_cost": shipping_cost, "inventory_accuracy": inventory_accuracy,
        })

    with open(os.path.join(OUTPUT_DIR, "daily_metrics.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    print(f"Generated {len(rows)} daily metric rows")

    # ── Per-category metrics ──────────────────────────────────────────────
    cat_rows = []
    vol_share_map = {
        "Electronics": 0.25, "Clothing": 0.22, "Home & Garden": 0.15,
        "Books": 0.10, "Sports & Outdoors": 0.08, "Beauty & Health": 0.08,
        "Toys & Games": 0.07, "Automotive": 0.05,
    }
    for date in daterange("2026-01-01", 180):
        for cat in categories:
            cat_vol = max(1, int(order_volume * vol_share_map[cat] * random.uniform(0.8, 1.2)))
            cat_return = return_rate + random.uniform(-2, 2)
            if cat == "Electronics" and "2026-03-22" <= date <= "2026-03-28":
                cat_return += random.uniform(5, 8)
            cat_return = max(0, round(cat_return, 1))
            cat_rev = round(cat_vol * random.uniform(50, 200), 2)
            cat_rating = round(random.uniform(3.5, 4.8), 2)
            cat_rows.append({
                "date": date, "category": cat, "order_volume": cat_vol,
                "return_rate": cat_return, "revenue": cat_rev, "avg_rating": cat_rating,
            })

    with open(os.path.join(OUTPUT_DIR, "daily_category_metrics.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cat_rows[0].keys())
        w.writeheader()
        w.writerows(cat_rows)
    print(f"Generated {len(cat_rows)} category metric rows")

    # ── Per-warehouse metrics ─────────────────────────────────────────────
    wh_base = {"A": 18.0, "B": 19.0, "C": 17.0}
    wh_headcount = {"A": 180, "B": 200, "C": 150}
    wh_rows = []
    for date in daterange("2026-01-01", 180):
        for wh in warehouses:
            wh_vol_share = {"A": 0.4, "B": 0.35, "C": 0.25}
            wh_vol = max(1, int(order_volume * wh_vol_share[wh] * random.uniform(0.85, 1.15)))
            fulfill = wh_base[wh] + random.uniform(-2, 3)
            if wh == "A" and i > 56:
                fulfill += 3.0 * ((i - 56) / 124)
            if wh == "B" and date == "2026-06-12":
                fulfill = 45.0
            hc = wh_headcount[wh]
            if wh == "A" and i > 56:
                hc = int(wh_headcount[wh] * (1 - 0.15 * ((i - 56) / 124)))
            wh_rows.append({
                "date": date, "warehouse": wh, "order_volume": wh_vol,
                "fulfillment_time_avg": round(fulfill, 1),
                "fulfillment_time_p95": round(fulfill * random.uniform(1.8, 2.4), 1),
                "headcount": hc,
            })

    with open(os.path.join(OUTPUT_DIR, "daily_warehouse_metrics.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=wh_rows[0].keys())
        w.writeheader()
        w.writerows(wh_rows)
    print(f"Generated {len(wh_rows)} warehouse metric rows")

    # ── Per-channel metrics ───────────────────────────────────────────────
    ch_rows = []
    for date in daterange("2026-01-01", 180):
        for ch in channels:
            ch_share = {"web": 0.50, "mobile": 0.40, "phone": 0.10}
            ch_vol = max(1, int(order_volume * ch_share[ch] * random.uniform(0.9, 1.1)))
            ch_wait = wait_base * random.uniform(0.7, 2.0)
            if ch == "mobile" and "2026-04-01" <= date <= "2026-04-14":
                ch_wait *= 2.5
            ch_csat = 4.5 - (ch_wait - 1.5) * 0.3 + random.uniform(-0.2, 0.2)
            if ch == "mobile" and "2026-04-01" <= date <= "2026-04-14":
                ch_csat -= 0.5
            ch_csat = max(3.0, min(5.0, round(ch_csat, 2)))
            ch_rows.append({
                "date": date, "channel": ch, "order_volume": ch_vol,
                "avg_wait_time_min": round(ch_wait, 1), "csat_score": ch_csat,
            })

    with open(os.path.join(OUTPUT_DIR, "daily_channel_metrics.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ch_rows[0].keys())
        w.writeheader()
        w.writerows(ch_rows)
    print(f"Generated {len(ch_rows)} channel metric rows")


# ---------------------------------------------------------------------------
# Weekly ops reports (Markdown)
# ---------------------------------------------------------------------------

WEEKLY_REPORTS = {
    "week_01_2026-01-06.md": (
        "# Weekly Ops Report - Week 1 (Jan 1-6, 2026)\n\n"
        "## Executive Summary\n"
        "Solid start to the year. Post-holiday volume is settling to normal seasonal levels. All KPIs within targets.\n\n"
        "## Key Metrics\n"
        "| Metric | This Week | Last Week | Target |\n"
        "|---|---|---|---|\n"
        "| Order Volume | 28,450 | 42,100 | " + EM + " |\n"
        "| Avg Fulfillment (hrs) | 18.2 | 21.4 | " + LE + " 24 |\n"
        "| Fulfillment p95 (hrs) | 42.1 | 48.3 | " + LE + " 48 |\n"
        "| Return Rate (%) | 7.1 | 9.8 | " + LE + " 8 |\n"
        "| CSAT | 4.4 | 4.1 | " + GE + " 4.2 |\n\n"
        "## What Went Well\n"
        "- Fulfillment times returned to normal after holiday peak\n"
        "- No critical incidents reported\n"
        "- Warehouse staffing at full capacity\n\n"
        "## Issues & Risks\n"
        "- Return rate slightly elevated in Clothing (8.9%) " + EM + " likely holiday gift returns, expected to normalize\n"
        "- None critical\n"
    ),
    "week_02_2026-01-13.md": (
        "# Weekly Ops Report - Week 2 (Jan 7-13, 2026)\n\n"
        "## Executive Summary\n"
        "Operations stable. Return rates normalizing. Fulfillment consistently under target.\n\n"
        "## Key Metrics\n"
        "| Metric | This Week | Last Week | Target |\n"
        "|---|---|---|---|\n"
        "| Order Volume | 27,100 | 28,450 | " + EM + " |\n"
        "| Avg Fulfillment (hrs) | 17.5 | 18.2 | " + LE + " 24 |\n"
        "| Return Rate (%) | 6.8 | 7.1 | " + LE + " 8 |\n"
        "| CSAT | 4.5 | 4.4 | " + GE + " 4.2 |\n\n"
        "## What Went Well\n"
        "- Clothing returns dropped to 7.2% (normalizing)\n"
        "- All three warehouses operating at target\n"
        "- CSAT improving\n\n"
        "## Issues & Risks\n"
        "- None\n"
    ),
    "week_03_2026-01-20.md": (
        "# Weekly Ops Report - Week 3 (Jan 14-20, 2026)\n\n"
        "## Executive Summary\n"
        "Routine week. No anomalies. Inventory accuracy remains above 98%.\n\n"
        "## Key Metrics\n"
        "| Metric | This Week | Last Week | Target |\n"
        "|---|---|---|---|\n"
        "| Order Volume | 26,800 | 27,100 | " + EM + " |\n"
        "| Avg Fulfillment (hrs) | 17.8 | 17.5 | " + LE + " 24 |\n"
        "| Return Rate (%) | 6.5 | 6.8 | " + LE + " 8 |\n"
        "| CSAT | 4.4 | 4.5 | " + GE + " 4.2 |\n\n"
        "## Issues & Risks\n"
        "- None\n"
    ),
    "week_04_2026-01-27.md": (
        "# Weekly Ops Report - Week 4 (Jan 21-27, 2026)\n\n"
        "## Executive Summary\n"
        "Quiet week. All metrics within targets. Preparing for February planning cycle.\n\n"
        "## Key Metrics\n"
        "| Metric | This Week | Last Week | Target |\n"
        "|---|---|---|---|\n"
        "| Order Volume | 27,500 | 26,800 | " + EM + " |\n"
        "| Avg Fulfillment (hrs) | 18.1 | 17.8 | " + LE + " 24 |\n"
        "| Return Rate (%) | 6.7 | 6.5 | " + LE + " 8 |\n"
        "| CSAT | 4.3 | 4.4 | " + GE + " 4.2 |\n\n"
        "## Issues & Risks\n"
        "- Minor: Warehouse B reported 2-hour delay on Tuesday due to carrier pickup timing\n"
    ),
    "week_05_2026-02-03.md": (
        "# Weekly Ops Report - Week 5 (Jan 28-Feb 3, 2026)\n\n"
        "## Executive Summary\n"
        "February volume starting to pick up. Fulfillment steady. February planning completed.\n\n"
        "## Key Metrics\n"
        "| Metric | This Week | Last Week | Target |\n"
        "|---|---|---|---|\n"
        "| Order Volume | 28,200 | 27,500 | " + EM + " |\n"
        "| Avg Fulfillment (hrs) | 18.3 | 18.1 | " + LE + " 24 |\n"
        "| Return Rate (%) | 6.9 | 6.7 | " + LE + " 8 |\n"
        "| CSAT | 4.4 | 4.3 | " + GE + " 4.2 |\n\n"
        "## Issues & Risks\n"
        "- None significant\n"
    ),
    "week_06_2026-02-10.md": (
        "# Weekly Ops Report - Week 6 (Feb 4-10, 2026)\n\n"
        "## Executive Summary\n"
        "All stable. No escalations. Fulfillment consistent across all warehouses.\n\n"
        "## Key Metrics\n"
        "| Metric | This Week | Last Week | Target |\n"
        "|---|---|---|---|\n"
        "| Order Volume | 29,100 | 28,200 | " + EM + " |\n"
        "| Avg Fulfillment (hrs) | 18.0 | 18.3 | " + LE + " 24 |\n"
        "| Return Rate (%) | 6.6 | 6.9 | " + LE + " 8 |\n"
        "| CSAT | 4.5 | 4.4 | " + GE + " 4.2 |\n\n"
        "## Issues & Risks\n"
        "- None\n"
    ),
    "week_07_2026-02-17.md": (
        "# Weekly Ops Report - Week 7 (Feb 11-17, 2026)\n\n"
        "## Executive Summary\n"
        "Solid performance. Valentine's Day surge handled well. Electronics category saw 12% volume increase.\n\n"
        "## Key Metrics\n"
        "| Metric | This Week | Last Week | Target |\n"
        "|---|---|---|---|\n"
        "| Order Volume | 32,400 | 29,100 | " + EM + " |\n"
        "| Avg Fulfillment (hrs) | 19.2 | 18.0 | " + LE + " 24 |\n"
        "| Return Rate (%) | 7.0 | 6.6 | " + LE + " 8 |\n"
        "| CSAT | 4.3 | 4.5 | " + GE + " 4.2 |\n\n"
        "## What Went Well\n"
        "- Valentine's Day surge: 13,200 orders on Feb 14 alone " + EM + " handled without SLA breach\n"
        "- Gift category (Beauty & Health) volume up 35%\n\n"
        "## Issues & Risks\n"
        "- Fulfillment slightly elevated due to volume spike\n"
    ),
    "week_08_2026-02-24.md": (
        "# Weekly Ops Report - Week 8 (Feb 18-24, 2026)\n\n"
        "## Executive Summary\n"
        "Volume returning to normal after Valentine's. However, Warehouse A fulfillment time is starting to trend upward "
        "" + EM + " 20.5 hrs avg vs 18.0 target. Early signs of staffing pressure.\n\n"
        "## Key Metrics\n"
        "| Metric | This Week | Last Week | Target |\n"
        "|---|---|---|---|\n"
        "| Order Volume | 28,800 | 32,400 | " + EM + " |\n"
        "| Avg Fulfillment (hrs) | 20.5 | 19.2 | " + LE + " 24 |\n"
        "| Fulfillment p95 (hrs) | 46.2 | 43.8 | " + LE + " 48 |\n"
        "| Return Rate (%) | 6.8 | 7.0 | " + LE + " 8 |\n"
        "| CSAT | 4.3 | 4.3 | " + GE + " 4.2 |\n\n"
        "## What Went Well\n"
        "- Warehouse B and C performing at target\n"
        "- No critical incidents\n\n"
        "## Issues & Risks\n"
        "- [Medium] Warehouse A fulfillment creeping up " + EM + " needs monitoring\n"
        "- [Low] Inventory accuracy at Warehouse A slightly below 98% threshold\n"
    ),
    "week_09_2026-03-03.md": (
        "# Weekly Ops Report - Week 9 (Feb 25-Mar 3, 2026)\n\n"
        "## Executive Summary\n"
        "Warehouse A issue persisting. Fulfillment avg now 21.8 hrs. Staffing shortage identified as root cause "
        "" + EM + " 15% below target headcount. Escalation to Tier-2 initiated.\n\n"
        "## Key Metrics\n"
        "| Metric | This Week | Last Week | Target |\n"
        "|---|---|---|---|\n"
        "| Order Volume | 28,100 | 28,800 | " + EM + " |\n"
        "| Avg Fulfillment (hrs) | 21.8 | 20.5 | " + LE + " 24 |\n"
        "| Fulfillment p95 (hrs) | 48.5 | 46.2 | " + LE + " 48 |\n"
        "| Return Rate (%) | 6.9 | 6.8 | " + LE + " 8 |\n"
        "| CSAT | 4.2 | 4.3 | " + GE + " 4.2 |\n\n"
        "## What Went Well\n"
        "- Other warehouses holding steady\n\n"
        "## Issues & Risks\n"
        "- [High] Warehouse A fulfillment breach of p95 threshold (48.5 hrs)\n"
        "- [Medium] Staffing shortage at Warehouse A not yet resolved\n"
        "- Hiring pipeline initiated but time-to-hire is 4-6 weeks\n"
    ),
    "week_10_2026-03-10.md": (
        "# Weekly Ops Report - Week 10 (Mar 4-10, 2026)\n\n"
        "## Executive Summary\n"
        "Warehouse A continues to degrade. Fulfillment avg 23.5 hrs, p95 at 51.2 hrs " + EM + " "
        "breaching critical threshold for p95. Tier-2 escalation active. "
        "NOTE: Despite the degradation, some improvement expected next week as temp staffing begins.\n\n"
        "## Key Metrics\n"
        "| Metric | This Week | Last Week | Target |\n"
        "|---|---|---|---|\n"
        "| Order Volume | 27,900 | 28,100 | " + EM + " |\n"
        "| Avg Fulfillment (hrs) | 23.5 | 21.8 | " + LE + " 24 |\n"
        "| Fulfillment p95 (hrs) | 51.2 | 48.5 | " + LE + " 48 |\n"
        "| Return Rate (%) | 7.1 | 6.9 | " + LE + " 8 |\n"
        "| CSAT | 4.1 | 4.2 | " + GE + " 4.2 |\n\n"
        "## Issues & Risks\n"
        "- [High] p95 Fulfillment breach for 2 consecutive weeks at Warehouse A\n"
        "- [Medium] CSAT dropped to 4.1 (below target)\n"
        "- Temporary staffing approved " + EM + " 20 temps starting Week 12\n"
        "- [Contradiction alert: Reports claim improvement expected but data continues degrading through Week 16]\n"
    ),
    "week_11_2026-03-17.md": (
        "# Weekly Ops Report - Week 11 (Mar 11-17, 2026)\n\n"
        "## Executive Summary\n"
        "Preparing for temp staff intake. Fulfillment still elevated. Mobile app v3.2 launched " + EM + " monitoring for issues.\n\n"
        "## Key Metrics\n"
        "| Metric | This Week | Last Week | Target |\n"
        "|---|---|---|---|\n"
        "| Order Volume | 28,500 | 27,900 | " + EM + " |\n"
        "| Avg Fulfillment (hrs) | 24.2 | 23.5 | " + LE + " 24 |\n"
        "| Fulfillment p95 (hrs) | 53.1 | 51.2 | " + LE + " 48 |\n"
        "| Return Rate (%) | 7.0 | 7.1 | " + LE + " 8 |\n"
        "| CSAT | 4.2 | 4.1 | " + GE + " 4.2 |\n\n"
        "## Issues & Risks\n"
        "- [High] Fulfillment avg breached 24hr target for first time\n"
        "- [Medium] Electronics return rate creeping up (9.1%)\n"
        "- Mobile app v3.2 launched " + EM + " CSAT on mobile channel at 4.0 (needs watching)\n"
    ),
    "week_12_2026-03-24.md": (
        "# Weekly Ops Report - Week 12 (Mar 18-24, 2026)\n\n"
        "## Executive Summary\n"
        "Multiple issues this week. Electronics return rate spiked to 14.2% " + EM + " "
        "identified as defective headphone batch from supplier. Fulfillment improvement at Warehouse A "
        "expected as 20 temps begin. However, we see some improvement already.\n\n"
        "## Key Metrics\n"
        "| Metric | This Week | Last Week | Target |\n"
        "|---|---|---|---|\n"
        "| Order Volume | 29,200 | 28,500 | " + EM + " |\n"
        "| Avg Fulfillment (hrs) | 24.8 | 24.2 | " + LE + " 24 |\n"
        "| Fulfillment p95 (hrs) | 54.5 | 53.1 | " + LE + " 48 |\n"
        "| Return Rate (%) | 8.5 | 7.0 | " + LE + " 8 |\n"
        "| CSAT | 4.0 | 4.2 | " + GE + " 4.2 |\n\n"
        "## What Went Well\n"
        "- Temp staffing started at Warehouse A (20 temp workers)\n"
        "- Defective headphones identified quickly (within 48 hours)\n\n"
        "## Issues & Risks\n"
        "- [Critical] Electronics return rate 14.2% (critical threshold breach)\n"
        "- [High] Fulfillment p95 at 54.5 hrs (critical breach)\n"
        "- [Medium] CSAT dropped to 4.0 " + EM + " driven by slow fulfillment\n"
        "- Supplier quality investigation opened for headphone batch\n"
    ),
    "week_13_2026-03-31.md": (
        "# Weekly Ops Report - Week 13 (Mar 25-31, 2026)\n\n"
        "## Executive Summary\n"
        "Headphone recall in progress. Fulfillment still elevated despite temp staff " + EM + " "
        "ramp-up slower than expected. Return rate improving as defective stock is cleared.\n\n"
        "## Key Metrics\n"
        "| Metric | This Week | Last Week | Target |\n"
        "|---|---|---|---|\n"
        "| Order Volume | 28,900 | 29,200 | " + EM + " |\n"
        "| Avg Fulfillment (hrs) | 25.3 | 24.8 | " + LE + " 24 |\n"
        "| Fulfillment p95 (hrs) | 55.8 | 54.5 | " + LE + " 48 |\n"
        "| Return Rate (%) | 7.8 | 8.5 | " + LE + " 8 |\n"
        "| CSAT | 4.0 | 4.0 | " + GE + " 4.2 |\n\n"
        "## Issues & Risks\n"
        "- [High] Fulfillment continues to degrade despite temps\n"
        "- [Medium] Headphone recall: 2,200 units returned so far, 800 still outstanding\n"
        "- Temp staff efficiency at 60% of permanent staff " + EM + " expected to reach 80% by Week 15\n"
    ),
    "week_14_2026-04-07.md": (
        "# Weekly Ops Report - Week 14 (Apr 1-7, 2026)\n\n"
        "## Executive Summary\n"
        "Mobile app issues detected. v3.2 rollout caused increased cart abandonment and wait times on mobile channel. "
        "Fulfillment still not improving " + EM + " contrary to earlier expectations, it worsened to 26.1 hrs avg. "
        "NOTE: The weekly report claims fulfillment is \"stabilizing\" but data shows continued degradation. "
        "This is an intentional inconsistency for agent testing.\n\n"
        "## Key Metrics\n"
        "| Metric | This Week | Last Week | Target |\n"
        "|---|---|---|---|\n"
        "| Order Volume | 27,500 | 28,900 | " + EM + " |\n"
        "| Avg Fulfillment (hrs) | 26.1 | 25.3 | " + LE + " 24 |\n"
        "| Fulfillment p95 (hrs) | 57.2 | 55.8 | " + LE + " 48 |\n"
        "| Return Rate (%) | 7.2 | 7.8 | " + LE + " 8 |\n"
        "| CSAT | 3.8 | 4.0 | " + GE + " 4.2 |\n\n"
        "## What Went Well\n"
        "- Headphone recall largely complete (2,850 of 3,000 units returned)\n"
        "- Electronics return rate normalizing (8.5%)\n\n"
        "## Issues & Risks\n"
        "- [Critical] Fulfillment p95 at 57.2 hrs " + EM + " critical breach\n"
        "- [High] CSAT dropped to 3.8 " + EM + " below critical threshold of 3.8\n"
        "- [High] Mobile app v3.2 causing increased wait times on mobile channel\n"
        "- [Medium] Cart abandonment on mobile increased from 68% to 76%\n"
        "- Engineering team working on hotfix (v3.2.1 expected Apr 10)\n"
    ),
    "week_15_2026-04-14.md": (
        "# Weekly Ops Report - Week 15 (Apr 8-14, 2026)\n\n"
        "## Executive Summary\n"
        "Mobile hotfix v3.2.1 deployed Apr 10. Mobile channel metrics improving but not fully recovered. "
        "Fulfillment stabilizing (the report claims this but actual data still shows 26.8 hrs). "
        "Temp staff at 75% efficiency.\n\n"
        "## Key Metrics\n"
        "| Metric | This Week | Last Week | Target |\n"
        "|---|---|---|---|\n"
        "| Order Volume | 27,200 | 27,500 | " + EM + " |\n"
        "| Avg Fulfillment (hrs) | 26.8 | 26.1 | " + LE + " 24 |\n"
        "| Fulfillment p95 (hrs) | 58.5 | 57.2 | " + LE + " 48 |\n"
        "| Return Rate (%) | 7.0 | 7.2 | " + LE + " 8 |\n"
        "| CSAT | 4.0 | 3.8 | " + GE + " 4.2 |\n\n"
        "## What Went Well\n"
        "- Mobile hotfix deployed " + EM + " mobile wait times reduced 35%\n"
        "- CSAT recovering\n"
        "- Headphone recall closed\n\n"
        "## Issues & Risks\n"
        "- [Critical] Fulfillment breach continues (8th consecutive week for Warehouse A)\n"
        "- [Medium] Temp staff still ramping\n"
        "- [Contradiction: Report says \"fulfillment stabilizing\" but data shows 26.1->26.8->continuing upward]\n"
    ),
    "week_16_2026-04-21.md": (
        "# Weekly Ops Report - Week 16 (Apr 15-21, 2026)\n\n"
        "## Executive Summary\n"
        "Week 16 shows mixed signals. The weekly report narrative is cautiously optimistic (\"improvement trajectory\") "
        "but the underlying KPI data tells a different story for fulfillment. Mobile channel fully recovered. "
        "Action items set for Q2.\n\n"
        "## Key Metrics\n"
        "| Metric | This Week | Last Week | Target |\n"
        "|---|---|---|---|\n"
        "| Order Volume | 28,100 | 27,200 | " + EM + " |\n"
        "| Avg Fulfillment (hrs) | 27.2 | 26.8 | " + LE + " 24 |\n"
        "| Fulfillment p95 (hrs) | 59.8 | 58.5 | " + LE + " 48 |\n"
        "| Return Rate (%) | 6.9 | 7.0 | " + LE + " 8 |\n"
        "| CSAT | 4.2 | 4.0 | " + GE + " 4.2 |\n\n"
        "## What Went Well\n"
        "- CSAT back to target (4.2)\n"
        "- Mobile channel fully recovered " + EM + " wait times back to normal\n"
        "- No new incidents this week\n\n"
        "## Issues & Risks\n"
        "- [Critical] Fulfillment continues to degrade " + EM + " Tier-3 escalation recommended\n"
        "- [High] p95 at 59.8 hrs " + EM + " worst level in 16 weeks\n"
        "- Q2 planning: need to address Warehouse A staffing permanently\n"
        "- [Contradiction: Report tone is \"cautiously optimistic\" but all fulfillment metrics are at worst levels]\n"
    ),
}

# ---------------------------------------------------------------------------
# Incident reports (Markdown)
# ---------------------------------------------------------------------------

INCIDENT_REPORTS = {
    "incident_001_conveyor_failure.md": (
        "# Incident Report: Warehouse B Conveyor Failure\n\n"
        "## Incident ID: INC-2026-001\n"
        "- Date: June 12, 2026\n"
        "- Duration: 6 hours (09:00-15:00 CT)\n"
        "- Severity: High\n"
        "- Reported By: David Kim (Director of Fulfillment)\n\n"
        "## Timeline\n"
        "- 08:45 " + EM + " Conveyor belt motor reported running hot\n"
        "- 09:00 " + EM + " Motor seized, belt stopped. Full stoppage of packing line 2\n"
        "- 09:15 " + EM + " Maintenance team dispatched\n"
        "- 10:30 " + EM + " Diagnosis: motor burnout (bearing failure), no spare available\n"
        "- 11:00 " + EM + " Emergency order placed with supplier (2hr delivery)\n"
        "- 13:00 " + EM + " Replacement motor arrived\n"
        "- 14:00 " + EM + " Installation complete\n"
        "- 15:00 " + EM + " Line back at full capacity\n\n"
        "## Impact\n"
        "- 2,500 orders delayed (avg +6 hours)\n"
        "- Fulfillment time for Warehouse B: 45 hrs avg on June 12\n"
        "- No customer-facing impact (all orders still delivered within committed window)\n\n"
        "## Root Cause\n"
        "Motor bearing reached end of life. No preventative replacement schedule. No spare motor kept onsite.\n\n"
        "## Action Items\n"
        "1. [Done] Order 2 spare motors for each warehouse\n"
        "2. [Done] Implement quarterly motor bearing inspection\n"
        "3. [In Progress] Create preventative maintenance schedule for all conveyor systems\n"
        "4. [Done] Add motor temperature monitoring sensors\n"
    ),
    "incident_002_headphone_defective_batch.md": (
        "# Incident Report: Defective Headphone Batch\n\n"
        "## Incident ID: INC-2026-002\n"
        "- Date Detected: March 22, 2026\n"
        "- Severity: High\n"
        "- Reported By: Lisa Park (VP Customer Experience)\n\n"
        "## Timeline\n"
        "- Mar 20 " + EM + " Return rate for Electronics begins unusual increase\n"
        "- Mar 21 " + EM + " 350 headphone returns received in single day (normal: ~40/day)\n"
        "- Mar 22 " + EM + " Quality team investigates; identifies batch number HP-2026-001\n"
        "- Mar 23 " + EM + " Supplier contacted; batch confirmed from single production run\n"
        "- Mar 24 " + EM + " Recall initiated; all customers who received units from affected batch notified\n"
        "- Mar 28 " + EM + " 2,200 of 3,000 affected units returned\n"
        "- Apr 7 " + EM + " Recall complete (2,850 returned, 150 lost/in-transit)\n\n"
        "## Impact\n"
        "- Return rate for Electronics: 14.2% (peak week Mar 22-28)\n"
        "- 3,000 units affected\n"
        "- Estimated revenue impact: $180,000 (refunds + shipping)\n"
        "- CSAT impact: -0.3 on Electronics category\n\n"
        "## Root Cause\n"
        "Supplier QA failure " + EM + " inadequate testing on production run. Sound distortion in left channel above 70% volume.\n\n"
        "## Action Items\n"
        "1. [Done] Supplier recall with full refund\n"
        "2. [Done] New incoming inspection SOP for audio products\n"
        "3. [In Progress] Diversify headphone supplier base (currently 100% single source)\n"
        "4. [Done] Alert customers proactively (not reactive)\n"
    ),
    "incident_003_mobile_app_regression.md": (
        "# Incident Report: Mobile App v3.2 Regression\n\n"
        "## Incident ID: INC-2026-003\n"
        "- Date Detected: April 1, 2026\n"
        "- Severity: High\n"
        "- Reported By: Priya Sharma (VP Engineering)\n\n"
        "## Timeline\n"
        "- Mar 30 " + EM + " Mobile app v3.2 deployed to production (100% rollout)\n"
        "- Apr 1 " + EM + " CSAT on mobile channel drops from 4.3 to 3.7\n"
        "- Apr 2 " + EM + " Cart abandonment on mobile increases from 68% to 78%\n"
        "- Apr 3 " + EM + " Root cause identified: cart timeout reduced from 30min to 10min (too aggressive)\n"
        "- Apr 4 " + EM + " Hotfix v3.2.1 developed, tested\n"
        "- Apr 10 " + EM + " Hotfix deployed (delayed due to testing " + EM + " cautious approach after previous incidents)\n"
        "- Apr 12 " + EM + " Mobile CSAT recovering to 4.0\n"
        "- Apr 18 " + EM + " Mobile CSAT fully recovered to 4.3\n\n"
        "## Impact\n"
        "- CSAT drop: 4.3 -> 3.7 on mobile (lowest channel score ever)\n"
        "- Cart abandonment: 68% -> 78% on mobile\n"
        "- Estimated revenue impact: $45,000 (lost carts over 10 days)\n"
        "- Overall CSAT affected: 4.2 -> 3.8 (company-wide low)\n\n"
        "## Root Cause\n"
        "Product decision to reduce cart timeout from 30min to 10min to reduce inventory holds, "
        "without sufficient user testing. No gradual rollout or A/B testing performed.\n\n"
        "## Action Items\n"
        "1. [Done] Rollback to 30min timeout via hotfix v3.2.1\n"
        "2. [Done] Add A/B testing requirement to deployment pipeline\n"
        "3. [In Progress] Create feature flag system for gradual rollouts\n"
        "4. [Done] Update deployment checklist to include CSAT monitoring\n"
    ),
    "incident_004_payment_gateway_outage.md": (
        "# Incident Report: Payment Gateway Outage\n\n"
        "## Incident ID: INC-2026-004\n"
        "- Date: July 5, 2026\n"
        "- Duration: 45 minutes (14:15-15:00 CT)\n"
        "- Severity: High\n"
        "- Reported By: Michael Okonkwo (VP Operations)\n\n"
        "## Timeline\n"
        "- 14:15 " + EM + " Payment gateway (Stripe) begins returning 429 rate limit errors\n"
        "- 14:20 " + EM + " Transactions failing; checkout blocked for all customers\n"
        "- 14:25 " + EM + " Ops team notified; engineering paged\n"
        "- 14:35 " + EM + " Root cause identified: Stripe rate limit hit due to misconfigured batch processing job\n"
        "- 14:45 " + EM + " Batch job throttled; rate limit restored\n"
        "- 15:00 " + EM + " Full transaction processing restored\n\n"
        "## Impact\n"
        "- 45 minutes of transaction blackout\n"
        "- ~850 orders delayed\n"
        "- Revenue impact: ~$85,000 in delayed transactions (all eventually processed)\n"
        "- No data loss\n\n"
        "## Root Cause\n"
        "A batch reconciliation job was misconfigured to send 10x normal API traffic, hitting Stripe's rate limit. "
        "No rate limiting on internal batch job.\n\n"
        "## Action Items\n"
        "1. [Done] Add rate limiting to internal batch jobs\n"
        "2. [Done] Implement fallback payment gateway (PayPal) as backup\n"
        "3. [In Progress] Add automatic failover between gateways\n"
        "4. [Done] Create runbook for payment gateway incidents\n"
    ),
    "incident_005_inventory_discrepancy.md": (
        "# Incident Report: Inventory Count Discrepancy " + EM + " Home & Garden\n\n"
        "## Incident ID: INC-2026-005\n"
        "- Date Detected: August 1, 2026\n"
        "- Severity: Medium\n"
        "- Reported By: David Kim (Director of Fulfillment)\n\n"
        "## Timeline\n"
        "- Jul 28 " + EM + " Weekly cycle count skipped at Warehouse B due to staffing shortage\n"
        "- Jul 31 " + EM + " Customer reports ordered \"Garden Tool Set\" received wrong item\n"
        "- Aug 1 " + EM + " Full audit of Home & Garden category at Warehouse B\n"
        "- Aug 1 " + EM + " 8% inventory variance found (worst in: garden tools, patio furniture)\n"
        "- Aug 2 " + EM + " Correction entries applied to WMS\n"
        "- Aug 3 " + EM + " Mandatory weekly cycle count policy re-emphasized\n\n"
        "## Impact\n"
        "- 8% inventory accuracy in Home & Garden at Warehouse B\n"
        "- ~120 incorrect shipments to customers over ~2 weeks\n"
        "- Estimated cost of return/refill: $4,500\n"
        "- No revenue loss (all customers either got correct item or received refund)\n\n"
        "## Root Cause\n"
        "Cycle count process skipped due to staffing. No automated alert when counts are missed. "
        "Inventory drifted as pickers corrected errors in system without verification.\n\n"
        "## Action Items\n"
        "1. [Done] Full reconciliation of Home & Garden category\n"
        "2. [Done] Mandatory weekly cycle counts reinstated\n"
        "3. [In Progress] Add automated alerts when cycle counts are missed\n"
        "4. [Planned] Implement cycle count compliance dashboard\n"
    ),
}

# ---------------------------------------------------------------------------
# Standard Operating Procedures (Markdown)
# ---------------------------------------------------------------------------

SOPS = {
    "sop_001_fulfillment_delay.md": (
        "# SOP-001: Fulfillment Delay Handling\n"
        "Version: 2.1 | Last Updated: 2025-12-01\n\n"
        "## Purpose\n"
        "Ensure consistent handling when fulfillment times exceed targets.\n\n"
        "## Triggers\n"
        "- Avg fulfillment time > 30 hours on any day\n"
        "- p95 fulfillment time > 55 hours on any day\n"
        "- Any warehouse exceeds 36 hours avg\n\n"
        "## Procedure\n"
        "1. **Identify bottleneck** (within 1 hour of breach):\n"
        "   - Check picking vs packing vs carrier pickup times\n"
        "   - Use fulfillment system dashboard\n"
        "2. **Alert Warehouse Lead** immediately\n"
        "3. **If > 36 hrs avg**: Trigger Tier-1 escalation via escalation tool\n"
        "4. **Communicate**: Update estimated delivery dates for affected orders\n"
        "5. **Log**: File root cause in incident tracker within 24 hours\n"
        "6. **Follow-up**: Review within 48 hours to confirm resolution\n\n"
        "## Escalation Criteria\n"
        "| Condition | Escalation Level |\n"
        "|---|---|\n"
        "| Single warehouse, single day > 36 hrs | Tier-1 |\n"
        "| Same warehouse, 2+ consecutive days > 36 hrs | Tier-2 |\n"
        "| Multiple warehouses, same day > 36 hrs | Tier-2 |\n"
        "| Any warehouse > 48 hrs | Tier-3 |\n"
    ),
    "sop_002_inventory_reconciliation.md": (
        "# SOP-002: Inventory Reconciliation\n"
        "Version: 1.3 | Last Updated: 2026-01-15\n\n"
        "## Purpose\n"
        "Maintain inventory accuracy >= 98% across all warehouses.\n\n"
        "## Weekly Cycle Count Procedure\n"
        "1. **Select SKUs**: 5% of SKUs per category (random stratified sampling)\n"
        "2. **Count**: Physical count by warehouse team\n"
        "3. **Compare**: Against WMS book quantity\n"
        "4. **If variance <= 2%**: No action needed\n"
        "5. **If variance 2-5%**: Recount immediately; if confirmed, adjust WMS\n"
        "6. **If variance > 5%**: Full category recount + Tier-1 escalation\n\n"
        "## Responsibilities\n"
        "- Warehouse Lead: Schedule and supervise counts\n"
        "- Inventory Analyst: Update WMS with adjustments\n"
        "- QA: Audit count accuracy quarterly\n\n"
        "## Compliance\n"
        "- Missed cycle count requires written explanation to Director of Fulfillment\n"
        "- Two consecutive misses trigger an automatic escalation\n"
    ),
    "sop_003_returns_processing.md": (
        "# SOP-003: Returns Processing\n"
        "Version: 2.0 | Last Updated: 2026-02-01\n\n"
        "## Purpose\n"
        "Process customer returns efficiently and accurately within 48 hours of receipt.\n\n"
        "## Procedure\n"
        "1. **Receive**: Log return receipt in Returns System\n"
        "2. **Inspect**: Within 48 hours of receipt at warehouse\n"
        "3. **Grade**:\n"
        "   - Grade A: Like-new condition -> restock at 90% value\n"
        "   - Grade B: Used but functional -> discount channel at 60% value\n"
        "   - Grade C: Damaged beyond use -> dispose/recycle\n"
        "4. **Update**: Record return reason code in system\n"
        "5. **Refund**: Process within 3 business days of receipt\n\n"
        "## Quality Triggers\n"
        "- Any category return rate > 12% -> Flag for quality review\n"
        "- Return rate above category average for 3+ consecutive weeks -> Supplier review\n"
        "- Single SKU return rate > 20% -> Immediate quality hold and investigation\n"
    ),
    "sop_004_monthly_ops_reporting.md": (
        "# SOP-004: Monthly Ops Reporting\n"
        "Version: 1.2 | Last Updated: 2025-11-01\n\n"
        "## Purpose\n"
        "Produce consistent monthly operations reports for leadership review.\n\n"
        "## Schedule\n"
        "- Data compilation: 1st-3rd business day of the month\n"
        "- Draft review: 4th business day\n"
        "- Final submission to VP Operations: 5th business day\n\n"
        "## Report Contents\n"
        "1. **Executive Summary** (1 page): Key takeaways, top issues, recommendations\n"
        "2. **KPI Dashboard**: Monthly actuals vs targets vs prior month\n"
        "3. **Variance Analysis**: >10% variance requires explanation\n"
        "4. **Incident Summary**: All incidents with severity Medium+\n"
        "5. **Top 3 Issues**: Current month's critical issues with action plan\n"
        "6. **Next Month Forecast**: Expected volume, known risks\n\n"
        "## Report Template\n"
        "Standard template is maintained in the Ops SharePoint. Each section has defined data sources and responsible owner.\n"
    ),
}

# ---------------------------------------------------------------------------
# Escalation logs (JSON)
# ---------------------------------------------------------------------------

ESCALATION_LOGS = [
    {"id": "ESC-001", "date": "2026-01-15", "tier": 1, "category": "Fulfillment",
     "reason": "Warehouse A fulfillment time 28.3 hrs (above 24 hr target)",
     "status": "Resolved", "resolution": "Additional staffing deployed, resolved within 24 hrs"},
    {"id": "ESC-002", "date": "2026-02-14", "tier": 1, "category": "Volume",
     "reason": "Valentine's Day volume surge 13,200 orders (250% of daily avg)",
     "status": "Resolved", "resolution": "Surge handled within SLA, no breach"},
    {"id": "ESC-003", "date": "2026-02-20", "tier": 1, "category": "Fulfillment",
     "reason": "Warehouse A fulfillment trending up (20.5 hrs)",
     "status": "Resolved", "resolution": "Monitoring initiated"},
    {"id": "ESC-004", "date": "2026-02-27", "tier": 2, "category": "Fulfillment",
     "reason": "Warehouse A fulfillment 21.8 hrs for 2nd week " + EM + " staffing shortage",
     "status": "In Progress", "resolution": "Temp staffing approved, starting Week 12"},
    {"id": "ESC-005", "date": "2026-03-06", "tier": 2, "category": "Fulfillment",
     "reason": "Warehouse A p95 fulfillment breached 48hr target (48.5 hrs)",
     "status": "In Progress", "resolution": "Temp hiring process started"},
    {"id": "ESC-006", "date": "2026-03-13", "tier": 2, "category": "Fulfillment",
     "reason": "Warehouse A p95 breach 2nd week (51.2 hrs)",
     "status": "In Progress", "resolution": "Temp staff onboarding Week 12"},
    {"id": "ESC-007", "date": "2026-03-20", "tier": 2, "category": "Fulfillment",
     "reason": "Warehouse A avg fulfillment 24.2 hrs " + EM + " breached target",
     "status": "In Progress", "resolution": "Temps starting next week"},
    {"id": "ESC-008", "date": "2026-03-22", "tier": 2, "category": "Quality",
     "reason": "Electronics return rate spike (14.2%) " + EM + " potential supplier issue",
     "status": "Resolved", "resolution": "Defective headphone batch identified, recall initiated"},
    {"id": "ESC-009", "date": "2026-03-25", "tier": 3, "category": "Quality",
     "reason": "Electronics return rate critical breach: supplier recall required",
     "status": "Resolved", "resolution": "COO notified, supplier recall completed"},
    {"id": "ESC-010", "date": "2026-04-01", "tier": 2, "category": "Technology",
     "reason": "Mobile app v3.2 CSAT drop (3.7 on mobile channel)",
     "status": "Resolved", "resolution": "Hotfix v3.2.1 deployed Apr 10"},
    {"id": "ESC-011", "date": "2026-04-02", "tier": 2, "category": "Fulfillment",
     "reason": "Warehouse A avg fulfillment 26.1 hrs " + EM + " ongoing degradation",
     "status": "In Progress", "resolution": "Temp staff efficiency at 60%, expected to improve"},
    {"id": "ESC-012", "date": "2026-04-03", "tier": 3, "category": "Technology",
     "reason": "Mobile cart abandonment 78% " + EM + " revenue impact > $45K",
     "status": "Resolved", "resolution": "Hotfix deployed, abandonment back to 68%"},
    {"id": "ESC-013", "date": "2026-04-08", "tier": 3, "category": "Fulfillment",
     "reason": "Warehouse A p95 at 57.2 hrs " + EM + " critical breach 8th week",
     "status": "In Progress", "resolution": "COO review scheduled, permanent hiring plan needed"},
    {"id": "ESC-014", "date": "2026-04-15", "tier": 3, "category": "Fulfillment",
     "reason": "Warehouse A p95 at 58.5 hrs " + EM + " worst on record",
     "status": "In Progress", "resolution": "Permanent hiring plan under discussion"},
    {"id": "ESC-015", "date": "2026-04-22", "tier": 3, "category": "Fulfillment",
     "reason": "Warehouse A p95 at 59.8 hrs " + EM + " escalation for Q2 planning",
     "status": "In Progress", "resolution": "Tier-3 escalation active, Q2 planning underway"},
    {"id": "ESC-016", "date": "2026-06-12", "tier": 2, "category": "Fulfillment",
     "reason": "Warehouse B conveyor failure (6 hr downtime)",
     "status": "Resolved", "resolution": "Motor replaced, spare parts policy updated"},
    {"id": "ESC-017", "date": "2026-06-13", "tier": 1, "category": "Fulfillment",
     "reason": "Catch-up from Warehouse B conveyor incident (2,500 delayed orders)",
     "status": "Resolved", "resolution": "All orders fulfilled within extended window"},
    {"id": "ESC-018", "date": "2026-07-05", "tier": 2, "category": "Technology",
     "reason": "Payment gateway outage (45 min) " + EM + " Stripe rate limit hit",
     "status": "Resolved", "resolution": "Batch job throttled, PayPal fallback added"},
    {"id": "ESC-019", "date": "2026-07-06", "tier": 1, "category": "Technology",
     "reason": "Follow-up on payment gateway incident " + EM + " runbook creation",
     "status": "Resolved", "resolution": "Payment incident runbook created and distributed"},
    {"id": "ESC-020", "date": "2026-08-01", "tier": 1, "category": "Inventory",
     "reason": "Home & Garden inventory discrepancy (8% variance at Warehouse B)",
     "status": "Resolved", "resolution": "Full reconciliation completed, cycle counts reinstated"},
]

# ---------------------------------------------------------------------------
# Product catalogue (static)
# ---------------------------------------------------------------------------

PRODUCT_CATEGORIES = [
    {"category": "Electronics", "subcategories": "smartphones,laptops,tablets,accessories,headphones",
     "avg_price": 245.00, "typical_return_rate": 12.0, "seasonal_peak": "November-December",
     "top_sku": "ELEC-SM-GALAXY-S25"},
    {"category": "Clothing", "subcategories": "mens,womens,kids,footwear,accessories",
     "avg_price": 65.00, "typical_return_rate": 15.0, "seasonal_peak": "January (post-holiday), September (fall collection)",
     "top_sku": "CLOTH-WM-DRESS-101"},
    {"category": "Home & Garden", "subcategories": "furniture,decor,kitchen,garden,tools",
     "avg_price": 120.00, "typical_return_rate": 5.0, "seasonal_peak": "April-May (spring)",
     "top_sku": "HOME-GRDN-TOOLSET-A1"},
    {"category": "Books", "subcategories": "fiction,non-fiction,textbooks,childrens",
     "avg_price": 18.00, "typical_return_rate": 2.0, "seasonal_peak": "August-September (back to school)",
     "top_sku": "BOOK-NF-LEADERSHIP-001"},
    {"category": "Sports & Outdoors", "subcategories": "fitness,camping,cycling,water-sports",
     "avg_price": 95.00, "typical_return_rate": 6.0, "seasonal_peak": "May-August",
     "top_sku": "SPORT-FIT-RUNNING-SHOE-X1"},
    {"category": "Beauty & Health", "subcategories": "skincare,supplements,personal-care,makeup",
     "avg_price": 35.00, "typical_return_rate": 4.0, "seasonal_peak": "February (Valentine's), November (holiday)",
     "top_sku": "BEAUTY-SKIN-SERUM-PRO"},
    {"category": "Toys & Games", "subcategories": "educational,board-games,video-games,outdoor-toys",
     "avg_price": 45.00, "typical_return_rate": 5.0, "seasonal_peak": "November-December",
     "top_sku": "TOYS-VG-CONSOLE-GEN5"},
    {"category": "Automotive", "subcategories": "parts,accessories,tools,car-care",
     "avg_price": 85.00, "typical_return_rate": 3.0, "seasonal_peak": "March-April (spring maintenance)",
     "top_sku": "AUTO-PART-BRAKE-PAD-C2"},
]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main():
    """Generate all synthetic data and write it to ``data/`` and ``data/docs/``."""
    os.makedirs(DOCS_DIR, exist_ok=True)

    for fname, content in HANDBOOK_SECTIONS.items():
        write_md(fname, content)
    print(f"Handbook: {len(HANDBOOK_SECTIONS)} sections written")

    generate_daily_metrics()

    for fname, content in WEEKLY_REPORTS.items():
        write_md(fname, content)
    print(f"Weekly Reports: {len(WEEKLY_REPORTS)} written")

    for fname, content in INCIDENT_REPORTS.items():
        write_md(fname, content)
    print(f"Incident Reports: {len(INCIDENT_REPORTS)} written")

    for fname, content in SOPS.items():
        write_md(fname, content)
    print(f"SOPs: {len(SOPS)} written")

    write_json("escalation_logs.json", ESCALATION_LOGS)
    print(f"Escalation Logs: {len(ESCALATION_LOGS)} written")

    with open(os.path.join(OUTPUT_DIR, "product_categories.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=PRODUCT_CATEGORIES[0].keys())
        w.writeheader()
        w.writerows(PRODUCT_CATEGORIES)
    print(f"Product Categories: {len(PRODUCT_CATEGORIES)} written")

    print("\nAll synthetic data generated successfully!")


if __name__ == "__main__":
    main()
