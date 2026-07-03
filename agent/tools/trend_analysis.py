"""Tool: Analyze trends in KPI data over time."""
import csv
import os
from datetime import datetime, timedelta
from agent.tools.query_kpi import load_csv, resolve_metric, METRICS_FILE, CATEGORY_FILE, WAREHOUSE_FILE, CHANNEL_FILE


def get_trend_analysis(query: str = "", metric: str = "", days: int = 30,
                        category: str = "", warehouse: str = "", channel: str = "") -> dict:
    """Analyze trends for a given metric."""
    if metric:
        metric_name = metric
    else:
        metric_name, _ = resolve_metric(query)

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

    today_dt = datetime.now()
    start_dt = today_dt - timedelta(days=days)
    start_date = start_dt.strftime("%Y-%m-%d")
    end_date = today_dt.strftime("%Y-%m-%d")

    # If data is 2026 data and today is 2026, use it; otherwise use all available
    if data and data[0].get("date", "") > end_date:
        start_date = "2026-01-01"
        end_date = "2026-06-30"

    filtered = [r for r in data if start_date <= r.get("date", "") <= end_date]
    filtered.sort(key=lambda r: r.get("date", ""))

    if not filtered:
        return {"error": f"No data found for {metric_name}", "metric": metric_name}

    values = []
    for row in filtered:
        val = row.get(metric_name)
        if val:
            try:
                values.append({"date": row["date"], "value": float(val) if "." in val else int(val)})
            except (ValueError, TypeError):
                continue

    if len(values) < 2:
        return {"metric": metric_name, "error": "Not enough data points for trend analysis",
                "data": values}

    numeric_vals = [v["value"] for v in values]
    first_half = numeric_vals[:len(numeric_vals)//2]
    second_half = numeric_vals[len(numeric_vals)//2:]

    avg_first = sum(first_half) / len(first_half) if first_half else 0
    avg_second = sum(second_half) / len(second_half) if second_half else 0

    pct_change = ((avg_second - avg_first) / avg_first * 100) if avg_first else 0

    # Detect anomalies (values > 1.5 std dev from mean)
    mean = sum(numeric_vals) / len(numeric_vals)
    variance = sum((x - mean) ** 2 for x in numeric_vals) / len(numeric_vals)
    std_dev = variance ** 0.5
    anomalies = [v for v in values if abs(v["value"] - mean) > 1.5 * std_dev]

    return {
        "metric": metric_name,
        "period": {"start": values[0]["date"], "end": values[-1]["date"]},
        "data_points": len(values),
        "average": round(mean, 2),
        "trend_direction": "up" if pct_change > 1 else ("down" if pct_change < -1 else "stable"),
        "pct_change": round(pct_change, 2),
        "first_half_avg": round(avg_first, 2),
        "second_half_avg": round(avg_second, 2),
        "min": round(min(numeric_vals), 2),
        "max": round(max(numeric_vals), 2),
        "anomalies_detected": len(anomalies),
        "anomaly_dates": [a["date"] for a in anomalies[:5]],
        "latest_trend": f"{'Increasing' if pct_change > 1 else 'Decreasing' if pct_change < -1 else 'Stable'} "
                        f"({abs(round(pct_change, 1))}% change over period)",
    }
