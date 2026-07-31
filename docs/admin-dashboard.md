# Administrator dashboard

Glideator includes a private operator cockpit at `/admin` for the single project administrator.

## Access

The dashboard uses the normal Glideator login and access-token flow. A user is treated as an administrator when either:

- the `users.role` database column is `admin`; or
- the normalized email appears in the comma-separated `ADMIN_EMAILS` environment variable.

For the current single-admin setup, configure the backend web service on Render with:

```text
ADMIN_EMAILS=<the email used for the Glideator account>
```

Log out and back in after changing the variable so `/auth/me` refreshes the effective role shown to the frontend.

## Included workflows

- **Overview** — latest GFS cycle, publication time, forecast horizon, site coverage, and Ground Crew resource coverage.
- **Forecast runs** — recent cycles grouped from the existing `predictions` table, including covered sites, horizon, row count, and complete/partial status.
- **Manual forecast check** — queues the existing `app.celery_app.check_and_trigger_forecast_processing` Celery task.
- **Site editor** — edits site coordinates, altitude, GFS point, country, information HTML, and tags.
- **Resource inventory** — shows validated local links, webcam counts, meteostation counts, extraction time, and sites with no resources.

No new database migration is required. Forecast-run state is derived from existing prediction records, while resources use the same bundled JSON or `glideator_ground_crew` SQL source as the public site-resource endpoint.

## API

All endpoints require an administrator bearer token:

```text
GET   /admin/overview
GET   /admin/forecast-runs
POST  /admin/forecast/check
GET   /admin/sites
PATCH /admin/sites/{site_id}
GET   /admin/resources
```

The manual action deliberately exposes the existing safe forecast-discovery task rather than a generic Celery command runner.
