# AI Prompt History

## AI Assistance Used

AI assistance was used to help structure the project, understand data quality monitoring requirements, create and review the Python pipeline, prepare sample CSV data, and develop automated tests and documentation.

## Prompts Used

- Help me build a Python data quality monitoring pipeline comparing baseline and current CSV batches.
- Help implement checks for row counts, null rates, duplicate keys, schema changes, numeric distributions, and data freshness.
- Help create sample datasets and unit tests for the pipeline.
- Help explain how to run the project and document its assumptions and limitations.

## Review and Validation

I ran `python main.py` successfully and reviewed the generated JSON report. I also ran `python -m unittest discover -s tests -v`; all three tests passed.

I reviewed the detected alerts and project structure. The current implementation uses configurable threshold-based checks and has limitations, including in-memory processing and basic alerting logic.
