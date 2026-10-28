"""Generate deterministic sample batches, including a few intentional quality issues."""
import csv
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

FIELDS = ["record_id", "event_timestamp", "customer_id", "amount"]


def make_batch(path, count, seed, bad=False):
    random.seed(seed)
    now = datetime.now(timezone.utc)
    rows = []
    for i in range(count):
        timestamp = now - timedelta(hours=random.randint(0, 12))
        amount = round(random.uniform(20, 120), 2)
        customer = f"C{random.randint(1, max(2, count // 2)):04d}"
        rows.append({
            "record_id": f"R{i+1:06d}",
            "event_timestamp": timestamp.isoformat(),
            "customer_id": customer,
            "amount": amount,
        })
    if bad and rows:
        # Deliberately introduce nulls, a duplicate key, and a distribution shift.
        for row in rows[:max(1, len(rows)//5)]:
            row["customer_id"] = ""
            row["amount"] = round(float(row["amount"]) * 2.5, 2)
        rows[-1]["record_id"] = rows[0]["record_id"]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    make_batch("data/baseline.csv", 100, 21, bad=False)
    make_batch("data/current.csv", 70, 22, bad=True)
    print("Created data/baseline.csv and data/current.csv")
