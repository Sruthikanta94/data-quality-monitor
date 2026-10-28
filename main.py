"""Batch data-quality monitor: compare a current CSV batch with a baseline batch."""
import argparse
import csv
import json
import statistics
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REQUIRED_COLUMNS = ["record_id", "event_timestamp", "customer_id", "amount"]
NUMERIC_COLUMNS = ["amount"]
KEY_COLUMN = "record_id"
TIMESTAMP_COLUMN = "event_timestamp"


def read_csv(path):
    with open(path, "r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"{path}: CSV has no header")
        return list(reader), list(reader.fieldnames)


def parse_timestamp(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        return None


def numeric_values(rows, column):
    values = []
    for row in rows:
        try:
            if row.get(column, "").strip() != "":
                values.append(float(row[column]))
        except (ValueError, TypeError):
            continue
    return values


def profile(rows, columns):
    result = {
        "row_count": len(rows),
        "columns": columns,
        "null_rates": {},
        "duplicate_key_count": 0,
        "invalid_timestamp_count": 0,
        "numeric": {},
        "latest_timestamp": None,
    }
    for col in columns:
        missing = sum(1 for row in rows if row.get(col) is None or str(row.get(col, "")).strip() == "")
        result["null_rates"][col] = round(missing / len(rows), 4) if rows else 0.0

    if KEY_COLUMN in columns:
        keys = [r.get(KEY_COLUMN, "").strip() for r in rows if r.get(KEY_COLUMN, "").strip()]
        result["duplicate_key_count"] = sum(count - 1 for count in Counter(keys).values() if count > 1)

    timestamps = []
    if TIMESTAMP_COLUMN in columns:
        for row in rows:
            ts = parse_timestamp(row.get(TIMESTAMP_COLUMN, ""))
            if ts:
                timestamps.append(ts)
            elif row.get(TIMESTAMP_COLUMN, "").strip():
                result["invalid_timestamp_count"] += 1
    if timestamps:
        result["latest_timestamp"] = max(timestamps).isoformat()

    for col in NUMERIC_COLUMNS:
        if col in columns:
            values = numeric_values(rows, col)
            result["numeric"][col] = {
                "valid_count": len(values),
                "mean": round(statistics.mean(values), 4) if values else None,
                "min": min(values) if values else None,
                "max": max(values) if values else None,
            }
    return result


def compare_profiles(baseline, current, null_rate_delta=0.10, volume_delta=0.20,
                     mean_delta=0.25, max_age_hours=48):
    alerts = []

    if baseline["columns"] != current["columns"]:
        alerts.append({
            "severity": "HIGH", "check": "schema",
            "message": f"Column list changed. Baseline={baseline['columns']}; current={current['columns']}"
        })

    base_count, cur_count = baseline["row_count"], current["row_count"]
    if base_count == 0:
        alerts.append({"severity": "HIGH", "check": "baseline", "message": "Baseline batch is empty; volume comparison skipped."})
    else:
        change = (cur_count - base_count) / base_count
        if abs(change) > volume_delta:
            alerts.append({
                "severity": "MEDIUM", "check": "volume",
                "message": f"Row count changed from {base_count} to {cur_count} ({change:+.1%}); threshold is ±{volume_delta:.0%}."
            })

    for col, cur_rate in current["null_rates"].items():
        base_rate = baseline["null_rates"].get(col)
        if base_rate is not None and cur_rate - base_rate > null_rate_delta:
            alerts.append({
                "severity": "MEDIUM", "check": "null_rate",
                "message": f"Null rate for '{col}' rose from {base_rate:.1%} to {cur_rate:.1%}."
            })

    for col, cur_stats in current["numeric"].items():
        base_stats = baseline["numeric"].get(col, {})
        bmean, cmean = base_stats.get("mean"), cur_stats.get("mean")
        if bmean is not None and cmean is not None and bmean != 0:
            change = (cmean - bmean) / abs(bmean)
            if abs(change) > mean_delta:
                alerts.append({
                    "severity": "MEDIUM", "check": "distribution",
                    "message": f"Mean of '{col}' changed from {bmean} to {cmean} ({change:+.1%}); threshold is ±{mean_delta:.0%}."
                })

    if current["duplicate_key_count"] > 0:
        alerts.append({
            "severity": "HIGH", "check": "duplicate_key",
            "message": f"Found {current['duplicate_key_count']} duplicate '{KEY_COLUMN}' key occurrence(s)."
        })
    if current["invalid_timestamp_count"] > 0:
        alerts.append({
            "severity": "MEDIUM", "check": "invalid_timestamp",
            "message": f"Found {current['invalid_timestamp_count']} non-empty timestamp value(s) that could not be parsed."
        })

    latest = parse_timestamp(current.get("latest_timestamp") or "")
    if latest:
        age_hours = (datetime.now(timezone.utc) - latest.astimezone(timezone.utc)).total_seconds() / 3600
        if age_hours > max_age_hours:
            alerts.append({
                "severity": "MEDIUM", "check": "freshness",
                "message": f"Latest record is {age_hours:.1f} hours old; maximum allowed age is {max_age_hours} hours."
            })
    elif current["row_count"] > 0:
        alerts.append({"severity": "HIGH", "check": "freshness", "message": "No valid event timestamp found; freshness could not be verified."})

    return alerts


def run_pipeline(baseline_path, current_path, output_path):
    baseline_rows, baseline_cols = read_csv(baseline_path)
    current_rows, current_cols = read_csv(current_path)

    missing_required = [c for c in REQUIRED_COLUMNS if c not in current_cols]
    if missing_required:
        raise ValueError(f"Current CSV is missing required columns: {missing_required}")

    base_profile = profile(baseline_rows, baseline_cols)
    current_profile = profile(current_rows, current_cols)
    alerts = compare_profiles(base_profile, current_profile)

    report = {
        "run_id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "status": "ALERT" if alerts else "PASS",
        "baseline_profile": base_profile,
        "current_profile": current_profile,
        "alert_count": len(alerts),
        "alerts": alerts,
        "assumptions": [
            "Each CSV represents one complete batch.",
            "Null-rate and distribution checks compare columns present in both profiles.",
            "Freshness uses event_timestamp and a default maximum age of 48 hours.",
            "Thresholds are simple configurable defaults, not learned statistical models."
        ]
    }
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description="Compare two CSV batches for data-quality changes.")
    parser.add_argument("--baseline", default="data/baseline.csv")
    parser.add_argument("--current", default="data/current.csv")
    parser.add_argument("--out", default="outputs/report.json")
    args = parser.parse_args()
    try:
        report = run_pipeline(args.baseline, args.current, args.out)
    except Exception as exc:
        parser.error(str(exc))
    print(f"Status: {report['status']} | rows: {report['current_profile']['row_count']} | alerts: {report['alert_count']}")
    for alert in report["alerts"]:
        print(f"[{alert['severity']}] {alert['check']}: {alert['message']}")
    print(f"Report written to {args.out}")


if __name__ == "__main__":
    main()
