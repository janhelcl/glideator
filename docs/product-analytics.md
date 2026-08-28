# Product analytics

Glideator records a small first-party event stream in the `product_events` table. The goal is to understand whether people reach useful forecasts and recommendations without introducing a third-party analytics SDK.

Known crawler traffic is classified at ingestion from the request User-Agent and stored separately in `bot_events`. This keeps the normal product analytics stream human-focused while preserving a lightweight view of crawler activity and the canonical bot identity.

MCP tool usage is also stored separately in `mcp_tool_events`. Each tool invocation records only the tool name, success/failure, execution duration, error class on failure, and timestamp. Prompts, tool arguments, IP addresses, MCP client metadata, and response payloads are not stored.

## Privacy properties

- No IP address, raw user agent, email address, account ID, or precise coordinates are stored.
- The request User-Agent is inspected transiently only to classify known bots; only the canonical bot name (for example `Googlebot` or `GPTBot`) is persisted in `bot_events`.
- The frontend sends only `window.location.pathname`, never the URL query string.
- Property keys that look like coordinates, IP addresses, emails, or user-agent data are removed client-side.
- Anonymous browser and session IDs are random identifiers stored in `localStorage` and `sessionStorage`.
- Global Privacy Control and Do Not Track are respected for frontend analytics.
- Set `REACT_APP_ANALYTICS_ENABLED=false` to disable frontend collection entirely.
- MCP analytics contain no browser identifiers and do not attempt to infer unique users or sessions.

The ingestion endpoint is `POST /analytics/events`. Payloads and event names are validated, property size is capped, and Redis-backed rate limits protect the endpoint. Known bots are diverted into `bot_events`; all other accepted events go to `product_events`.

## Event catalog

| Event | Meaning | Important properties |
| --- | --- | --- |
| `page_view` | A route was displayed | `route` |
| `map_metric_changed` | The map XC threshold changed | `previous_metric`, `metric` |
| `map_date_changed` | The map forecast date changed | `previous_date`, `date`, `metric` |
| `site_detail_viewed` | A site detail route opened | `site_id`, `date`, `metric`, `tab` |
| `site_date_changed` | The selected site forecast date changed | `site_id`, `previous_date`, `date`, `metric` |
| `site_metric_changed` | The selected site XC threshold changed | `site_id`, `previous_metric`, `metric`, `date` |
| `site_tab_changed` | The site detail tab changed | `site_id`, `previous_tab`, `tab` |
| `trip_plan_submitted` | The user explicitly submitted Trip Planner criteria | dates, metric, enabled filter flags, tag count |
| `trip_plan_results_viewed` | A distinct Trip Planner query returned | dates, metric, counts, enabled filter flags |
| `trip_plan_site_opened` | A suggested site was opened | `site_id`, metric, view, sort, flyability |
| `trip_plan_view_changed` | Trip Planner switched between list and map | `previous_view`, `view` |
| `trip_plan_sort_changed` | Trip Planner sorting changed | `previous_sort`, `sort` |
| `trip_plan_more_requested` | More recommendations were requested | visible and total counts |
| `recommendation_feedback_submitted` | Contextual helpful/not-helpful feedback | `surface`, `rating`, and recommendation context |

## Bot detection

Known bots are matched against explicit User-Agent signatures and stored with a canonical name. The list covers major search crawlers, AI crawlers/fetchers, social preview bots, and common SEO crawlers. Unknown automation is intentionally left in the normal stream rather than guessed from broad strings such as `bot` or `crawler`.

The administrator cockpit exposes a dedicated **Bots** tab with bot events, sessions, anonymous visitor IDs, and a per-bot breakdown for the selected time window.

## MCP usage analytics

All eight public MCP tools are instrumented at the tool boundary. Analytics writes are fail-open: if the analytics database write fails, the underlying MCP call still succeeds or fails exactly as it otherwise would.

The administrator cockpit exposes a dedicated **MCP** tab showing total tool calls, success rate, average execution duration, distinct tools used, and a per-tool breakdown. This stream intentionally does not report "users" or "sessions" because the server does not have a stable privacy-preserving MCP identity to support those metrics.

Example query:

```sql
select
    tool_name,
    count(*) as calls,
    count(*) filter (where success) as successful_calls,
    round(avg(duration_ms), 1) as avg_duration_ms
from mcp_tool_events
group by 1
order by calls desc, tool_name;
```

## Starter queries

Daily active anonymous visitors:

```sql
select
    date_trunc('day', created_at) as day,
    count(distinct anonymous_id) as visitors
from product_events
group by 1
order by 1 desc;
```

Bot traffic by crawler:

```sql
select
    bot_name,
    count(*) as events,
    count(distinct session_id) as sessions,
    count(distinct anonymous_id) as visitors
from bot_events
group by 1
order by events desc, bot_name;
```

Trip Planner funnel by day:

```sql
select
    date_trunc('day', created_at) as day,
    count(*) filter (where event_name = 'trip_plan_submitted') as submitted,
    count(*) filter (where event_name = 'trip_plan_results_viewed') as results_viewed,
    count(*) filter (where event_name = 'trip_plan_site_opened') as sites_opened
from product_events
where event_name in (
    'trip_plan_submitted',
    'trip_plan_results_viewed',
    'trip_plan_site_opened'
)
group by 1
order by 1 desc;
```

Feedback by surface:

```sql
select
    properties ->> 'surface' as surface,
    properties ->> 'rating' as rating,
    count(*) as responses
from product_events
where event_name = 'recommendation_feedback_submitted'
group by 1, 2
order by 1, 2;
```

Forecast feedback by site and metric:

```sql
select
    (properties ->> 'site_id')::integer as site_id,
    properties ->> 'metric' as metric,
    count(*) filter (where properties ->> 'rating' = 'helpful') as helpful,
    count(*) filter (where properties ->> 'rating' = 'not_helpful') as not_helpful
from product_events
where event_name = 'recommendation_feedback_submitted'
  and properties ->> 'surface' = 'site_forecast'
group by 1, 2
having count(*) >= 5
order by not_helpful desc, helpful asc;
```

## Suggested first dashboard

Start with four panels:

1. Daily active anonymous visitors and sessions.
2. Map-to-site engagement: site-detail views divided by map page views.
3. Trip Planner funnel: submitted → results viewed → site opened.
4. Helpful rate by `surface`, then by site and metric once sample sizes are meaningful.

Treat low-volume slices cautiously. A minimum of five responses is a useful display threshold, not a statistical guarantee.
