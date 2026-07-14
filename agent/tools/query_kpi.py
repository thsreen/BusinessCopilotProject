
import csv
import os
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# Paths – resolved relative to the project root (three levels up from this
# file: agent/tools/ → agent/ → project root).
# ---------------------------------------------------------------------------
DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data"
)
METRICS_FILE = os.path.join(DATA_DIR, "daily_metrics.csv")
CATEGORY_FILE = os.path.join(DATA_DIR, "daily_category_metrics.csv")
WAREHOUSE_FILE = os.path.join(DATA_DIR, "daily_warehouse_metrics.csv")
CHANNEL_FILE = os.path.join(DATA_DIR, "daily_channel_metrics.csv")

# Maps user-friendly phrases to canonical CSV column names.
# The key is a substring that may appear in a user's natural-language query;
# the value is the actual column header used in the CSV files.
METRIC_ALIASES = {
    "order volume": "order_volume",
    "fulfillment time": "fulfillment_time_avg",
    "fulfillment": "fulfillment_time_avg",
    "fulfillment time avg": "fulfillment_time_avg",
    "fulfillment time p95": "fulfillment_time_p95",
    "return rate": "return_rate",
    "returns": "return_rate",
    "return volume": "return_volume",
    "wait time": "avg_wait_time_min",
    "csat": "csat_score",
    "customer satisfaction": "csat_score",
    "revenue": "revenue",
    "units shipped": "units_shipped",
    "shipping cost": "shipping_cost",
    "inventory accuracy": "inventory_accuracy",
}

def load_csv(filepath: str) -> list[dict]:

    if not os.path.exists(filepath):
        return []
    with open(filepath, "r") as f:
        return list(csv.DictReader(f))

def parse_period(period: str) -> tuple[str, str]:

    today = datetime.now()
    period_lower = period.lower()
    if "last 7" in period_lower or "7 day" in period_lower or "week" in period_lower:
        start = (today - timedelta(days=7)).strftime("%Y-%m-%d")
        return start, today.strftime("%Y-%m-%d")
    elif "last 14" in period_lower or "14 day" in period_lower or "2 week" in period_lower:
        start = (today - timedelta(days=14)).strftime("%Y-%m-%d")
        return start, today.strftime("%Y-%m-%d")
    elif "last 30" in period_lower or "30 day" in period_lower or "month" in period_lower:
        start = (today - timedelta(days=30)).strftime("%Y-%m-%d")
        return start, today.strftime("%Y-%m-%d")
    elif "last 90" in period_lower or "90 day" in period_lower or "quarter" in period_lower:
        start = (today - timedelta(days=90)).strftime("%Y-%m-%d")
        return start, today.strftime("%Y-%m-%d")
    elif "this week" in period_lower:
        # Monday of the current week
        start = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")
        return start, today.strftime("%Y-%m-%d")
    elif "this month" in period_lower:
        start = today.replace(day=1).strftime("%Y-%m-%d")
        return start, today.strftime("%Y-%m-%d")
    # Fallback: the entire available 2026 window
    return "2026-01-01", "2026-06-30"

def resolve_metric(query: str) -> tuple[str, str]:

    query_lower = query.lower()
    for alias, metric in METRIC_ALIASES.items():
        if alias in query_lower:
            return metric, alias
    return "order_volume", "order volume"

def query_kpi_data(
    query: str = "",
    metric: str = "",
    period: str = "last 30 days",
    category: str = "",
    warehouse: str = "",
    channel: str = "",
) -> dict:

    # Resolve the metric name – explicit *metric* parameter wins over *query*
    if metric:
        metric_name = metric
    else:
        metric_name, display_name = resolve_metric(query)

    start_date, end_date = parse_period(period)

    # Select the correct CSV source based on the most specific filter
    # The priority order is: category > warehouse > channel > aggregate
    if category:
        data = load_csv(CATEGORY_FILE)
        data = [r for r in data if r.get("category", "").lower() == category.lower()]
    elif warehouse:
        data = load_csv(WAREHOUSE_FILE)
        data = [r for r in data if r.get("warehouse", "").upper() == warehouse.upper()]
    elif channel:
        data = load_csv(CHANNEL_FILE)
        data = [r for r in data if r.get("channel", "").lower() == channel.lower()]
    else:
        data = load_csv(METRICS_FILE)

    # Filter by date range and sort chronologically
    filtered = [r for r in data if start_date <= r.get("date", "") <= end_date]
    filtered.sort(key=lambda r: r.get("date", ""))

    if not filtered:
        return {
            "error": f"No data found for period {period}",
            "metric": metric_name,
            "data": [],
        }

    def _parse_value(v: str) -> float | int | None:
        """Convert a CSV cell string to a numeric type.

        Returns *None* for empty, null, or unparseable values instead of
        raising — this lets the caller skip bad data points gracefully.
        """
        if not v or v == "":
            return None
        try:
            return float(v) if "." in v else int(v)
        except (ValueError, TypeError):
            return None

    def _extract(rows: list[dict], col: str) -> list[dict]:
        """Extract ``(date, value)`` dicts for a given column.

        Only rows where the cell parses successfully are included; rows
        with missing or invalid values are silently skipped.
        """
        out = []
        for row in rows:
            parsed = _parse_value(row.get(col, ""))
            if parsed is not None:
                out.append({"date": row["date"], "value": parsed})
        return out

    values = _extract(filtered, metric_name)

    # Fallback: if the requested column yielded no data, try to find
    # *any* numeric column in the first row as a best-effort fallback.
    if not values:
        sample = filtered[0]
        fallback_col = None
        for col in sample.keys():
            if col in ("date", "category", "warehouse", "channel"):
                continue
            if _parse_value(sample.get(col, "")) is not None:
                fallback_col = col
                break
        if fallback_col:
            metric_name = fallback_col
            values = _extract(filtered, metric_name)

    if values:
        numeric_vals = [
            v["value"] for v in values if isinstance(v["value"], (int, float))
        ]
        avg_val = sum(numeric_vals) / len(numeric_vals) if numeric_vals else 0
        return {
            "metric": metric_name,
            "period": {"start": start_date, "end": end_date},
            "records": len(values),
            "average": round(avg_val, 2),
            "min": round(min(numeric_vals), 2) if numeric_vals else None,
            "max": round(max(numeric_vals), 2) if numeric_vals else None,
            "latest_value": values[-1]["value"] if values else None,
            "data": values[-10:],  # Only the last 10 data points to keep the response small
        }

    return {
        "error": f"Metric '{metric_name}' not found in data",
        "metric": metric_name,
        "data": [],
    }
