# Ground Crew CLI

Utilities for ingesting and managing candidate retrieval and validation runs.

## Commands

- `ground-crew load-jsonl <path>` loads a JSONL file of completed runs into the mart.
- `ground-crew load-single <path>` loads a single JSON payload.
- `ground-crew manual-run` lets you enter a run interactively.
- `ground-crew candidate-run` executes the BrowserUse `CandidateRetrievalAgent` end‑to‑end and writes a JSONL file (defaults to `outputs/candidate_retrieval_results.jsonl`).
- `ground-crew candidate-validate` replays candidates through a real browser, stores append-only validation rows, and (optionally) emits a JSONL artifact.
- `ground-crew candidate-validate-manual` records a manual decision for an existing candidate_id (handy after reviewing a link yourself).

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

1. Ensure `.env` has the required `DB_*` credentials, run `playwright install chromium`, and apply the updated schema in `sql/db_schema_glideator_ground_crew.sql` (new `candidate_validation_runs` + `candidate_validations` tables).
2. Generate data: `poetry run ground-crew candidate-run --site-id 1 --limit 1 --output outputs/test_run.jsonl`.
3. Load a couple of rows: `poetry run ground-crew load-jsonl outputs/test_run.jsonl`.
4. Validate them automatically:

```
poetry run ground-crew candidate-validate \
  --site-id 1 \
  --limit 2 \
  --output outputs/validation_results.jsonl
```

5. Inspect `outputs/validation_results.jsonl` and confirm new rows exist in `glideator_ground_crew.candidate_validations`.
6. Try a manual entry: `poetry run ground-crew candidate-validate-manual --candidate-id <id>` and verify the appended row in the same table.

## Validation Filters & Options

```
poetry run ground-crew candidate-validate \
  --only-unvalidated \
  --retry-failed \
  --host example.com \
  --validated-by NightlyCheck \
  --timeout-ms 20000 \
  --no-headless
```

- `--candidate-id/-c` or `--site-id/-s` narrow the batch.
- `--only-unvalidated` picks candidates with zero historical validations.
- `--retry-failed` selects links whose latest validation was not `ok`.
- `--output` writes JSONL rows containing the candidate record plus the validation payload (matching what gets persisted).
- `--validated-by` labels who/what performed the check so you can differentiate manual vs. automated runs later.
- Browser settings (timeout/headless) mirror the Playwright-backed validator in `ground_crew/validation/browser_check.py`.


