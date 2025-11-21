# Ground Crew CLI

Utilities for ingesting and managing candidate retrieval runs.

## Commands

- `ground-crew load-jsonl <path>` loads a JSONL file of completed runs into the mart.
- `ground-crew load-single <path>` loads a single JSON payload.
- `ground-crew manual-run` lets you enter a run interactively.
- `ground-crew candidate-run` executes the BrowserUse `CandidateRetrievalAgent` end‑to‑end and writes a JSONL file (defaults to `outputs/candidate_retrieval_results.jsonl`).

### Candidate Runner Options

```
poetry run ground-crew candidate-run \
  --site-id 1 --site-id 2 \
  --limit 1 \
  --output outputs/candidate_retrieval_results.jsonl
```

- `--site-id` can be repeated to target specific sites.
- `--limit` caps the number of rows processed after all filters are applied.
- `--output` selects the JSONL destination; results stay compatible with `load_extraction_run`.

## Smoke Test

1. Ensure `.env` has the required `DB_*` credentials and `playwright install chromium` has been run.
2. Run `poetry run ground-crew candidate-run --site-id 1 --limit 1 --output outputs/test_run.jsonl`.
3. Confirm the command logs success in the terminal and that `outputs/test_run.jsonl` contains a record with `result.structured_output.candidate_websites`.
4. (Optional) Load the result using `poetry run ground-crew load-jsonl outputs/test_run.jsonl`.


