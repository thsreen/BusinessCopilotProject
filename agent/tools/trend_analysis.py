
import csv
import os
from datetime import datetime, timedelta
from agent.tools.query_kpi import (
    load_csv,
    resolve_metric,
    METRICS_FILE,
    CATEGORY_FILE,
    WAREHOUSE_FILE,
    CHANNEL_FILE,
)

def get_trend_analysis(
    query: str = "",
    metric: str = "",
    days: int = 30,
    category: str = "",
    warehouse: str = "",
    channel: str = "",
) -> dict:

    # Resolve metric name – explicit parameter wins over free-text query
    if metric:
        metric_name = metric
    else:
        metric_name, _ = resolve_metric(query)

    # Select CSV data source (same priority logic as query_kpi)
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

    # Guard: if the earliest record is *after* today (e.g. the dataset is
    # frozen at 2026 and today is 2025/2026), fall back to the full 2026
    # window so we don't return an empty result.
    if data and data[0].get("date", "") > end_date:
        start_date = "2026-01-01"
        end_date = "2026-06-30"

    filtered = [r for r in data if start_date <= r.get("date", "") <= end_date]
    filtered.sort(key=lambda r: r.get("date", ""))

    if not filtered:
        return {"error": f"No data found for {metric_name}", "metric": metric_name}

    # Parse the column values into a list of {date, value} dicts
    values = []
    for row in filtered:
        val = row.get(metric_name)
        if val:
            try:
                values.append(
                    {
                        "date": row["date"],
                        "value": float(val) if "." in val else int(val),
                    }
                )
            except (ValueError, TypeError):
                continue

    if len(values) < 2:
        return {
            "metric": metric_name,
            "error": "Not enough data points for trend analysis",
            "data": values,
        }

    numeric_vals = [v["value"] for v in values]

    # Split the series in half for a simple directional comparison
    first_half = numeric_vals[: len(numeric_vals) // 2]
    second_half = numeric_vals[len(numeric_vals) // 2 :]

    avg_first = sum(first_half) / len(first_half) if first_half else 0
    avg_second = sum(second_half) / len(second_half) if second_half else 0

    # Percentage change from the first half to the second half
    pct_change = ((avg_second - avg_first) / avg_first * 100) if avg_first else 0

    # Anomaly detection: values more than 1.5 standard deviations from the mean
    mean = sum(numeric_vals) / len(numeric_vals)
    variance = sum((x - mean) ** 2 for x in numeric_vals) / len(numeric_vals)
    std_dev = variance ** 0.5
    anomalies = [
        v for v in values if abs(v["value"] - mean) > 1.5 * std_dev
    ]

    # Classify trend: use a ±1% deadband to avoid flagging tiny fluctuations
    if pct_change > 1:
        trend_dir = "up"
    elif pct_change < -1:
        trend_dir = "down"
    else:
        trend_dir = "stable"

    return {
        "metric": metric_name,
        "period": {"start": values[0]["date"], "end": values[-1]["date"]},
        "data_points": len(values),
        "average": round(mean, 2),
        "trend_direction": trend_dir,
        "pct_change": round(pct_change, 2),
        "first_half_avg": round(avg_first, 2),
        "second_half_avg": round(avg_second, 2),
        "min": round(min(numeric_vals), 2),
        "max": round(max(numeric_vals), 2),
        "anomalies_detected": len(anomalies),
        "anomaly_dates": [a["date"] for a in anomalies[:5]],
        "latest_trend": (
            f"{'Increasing' if pct_change > 1 else 'Decreasing' if pct_change < -1 else 'Stable'} "
            f"({abs(round(pct_change, 1))}% change over period)"
        ),
    }
