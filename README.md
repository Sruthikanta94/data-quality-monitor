# Batch Data Quality Monitor

A small, reproducible Python data-engineering project that profiles a baseline CSV batch, compares a later batch, and writes explainable data-quality alerts as JSON.

## Architecture

CSV baseline + current batch -> CSV reader -> schema and profile checks -> comparison rules -> JSON report.

## Requirements

- Python 3.9 or later
- No third-party packages required

## Quick start

From this folder, run:

```bash
python generate_sample_data.py
python main.py --baseline data/baseline.csv --current data/current.csv --out outputs/report.json
python -m unittest discover -s tests -v
```

The sample generator uses fixed random seeds and intentionally introduces a volume change, missing customer IDs, duplicate IDs, and a numeric distribution shift. Timestamps are generated near the current time so the freshness check can be exercised.

## Input schema

| Column | Type | Rule |
|---|---|---|
| record_id | string | Required; duplicate occurrences are reported |
| event_timestamp | ISO-8601 timestamp | Required; used for freshness |
| customer_id | string | Required; null rate is monitored |
| amount | numeric | Numeric values are profiled and mean shifts monitored |

## Output

`outputs/report.json` contains a run ID, status, baseline profile, current profile, alert count, human-readable alerts, and assumptions. A PASS means no configured rule triggered; it does not guarantee every possible data issue is absent.

## Current rules and defaults

- Volume change: alert when absolute change is greater than 20%.
- Null rate: alert when a column's null rate increases by more than 10 percentage points.
- Numeric distribution: alert when the mean changes by more than 25%.
- Freshness: alert when the latest valid timestamp is older than 48 hours.
- Schema, duplicate key, and invalid timestamp checks.

Thresholds are intentionally simple, interpretable defaults. For production use, thresholds should be configurable, and distribution checks could use quantiles or statistical tests.

## Error handling and limitations

- Missing required columns in the current batch cause a clear error.
- Duplicate records are reported; this starter does not silently delete source data.
- The program is designed for complete CSV batches, not streaming data.
- Partial-file recovery, database publishing, alert delivery, and very large distributed processing are not implemented.
- The report records assumptions so reviewers can see what is and is not covered.

## Performance note

The current implementation loads a CSV batch into memory, so memory use grows with input size. For larger datasets, use chunked CSV processing or a distributed engine such as PySpark. Measure runtime on the target machine before choosing an optimization.

## AI assistance and prompt history

The recruitment FAQ permits AI tools and asks candidates to preserve prompts. Add your actual prompts and note what you reviewed or changed. Example entry format:

- Tool: ChatGPT
- Prompt: “Help me break down the data-quality monitoring challenge into a small testable Python pipeline.”
- Use: Planning and starter-code assistance.
- Verification: I ran the sample pipeline and unit tests, inspected the JSON report, and reviewed the implementation.
- Changes I made: [write the changes you personally made].
