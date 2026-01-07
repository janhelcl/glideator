# ADR 001: Notification System Architecture

## Status

Accepted

## Context

Glideator needs to notify users when weather forecasts meet their specified conditions (e.g., "notify me when XC flying probability at Site X exceeds 50%").

Key constraints:

1. **Variable forecast timing**: GFS weather forecasts update 4 times daily at approximately 00:00, 06:00, 12:00, and 18:00 UTC. The exact arrival time varies due to processing delays.

2. **Forecast evolution**: A single forecast date may be updated multiple times as new GFS data arrives. Users should be notified of significant changes, but not spammed with every minor fluctuation.

3. **Lead time requirements**: Users want advance notice (e.g., 24-48 hours before a flyable day) to plan trips.

## Decision

### Polling Strategy

Use a 30-minute Celery Beat schedule to evaluate notifications continuously rather than triggering on forecast arrival. This ensures:
- Notifications are sent promptly regardless of when forecasts arrive
- No dependency on forecast pipeline completion events
- Resilience to processing delays or retries

### State Tracking

Introduce a `NotifiedForecast` table to track notification state per (notification_rule, forecast_date) pair:

| Field | Purpose |
|-------|---------|
| `notification_id` | Links to the user's notification rule |
| `forecast_date` | The date being forecast |
| `last_value` | Previous prediction value (0-1 scale) |
| `last_event_type` | Type of last notification sent |
| `notified_at` | Timestamp of last notification |

This enables detection of forecast evolution without re-notifying for unchanged conditions.

### Event Types

Three notification event types capture different scenarios:

| Event Type | Trigger Condition |
|------------|-------------------|
| `initial` | First time threshold is met for a forecast date |
| `deteriorated` | Previously above threshold, now below |
| `improved` | Currently above threshold AND improvement >= `improvement_threshold` |

The `improvement_threshold` (default 15%) prevents notifications for minor forecast fluctuations while still alerting users to significant positive changes.

### Delivery

Use Web Push Protocol (RFC 8030) with VAPID authentication for browser push notifications. This provides:
- No dependency on third-party notification services
- Works across browsers (Chrome, Firefox, Edge, Safari)
- Encrypted end-to-end delivery

## Components

```
┌─────────────────────────────────────────────────────────────────┐
│  GFS Forecast Updates (~00:00, 06:00, 12:00, 18:00 UTC)        │
│  Exact timing varies by 30-90 minutes                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Forecast Processing Pipeline                                   │
│  - Downloads GFS data                                           │
│  - Generates predictions for all sites/metrics                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Celery Beat: dispatch_notifications() [every 30 minutes]      │
│  - Catches forecast updates regardless of arrival time          │
│  - Provides consistent evaluation cadence                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  evaluate_and_queue_notifications()                            │
│  1. Fetch all active notification rules                         │
│  2. Fetch predictions within lead_time window                   │
│  3. Compare against NotifiedForecast state                      │
│  4. Determine event type (initial/deteriorated/improved)        │
│  5. Create NotificationEvent audit records                      │
│  6. Update NotifiedForecast state                               │
│  7. Send via Web Push                                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  User's Browser                                                 │
│  Service Worker receives push, displays notification            │
└─────────────────────────────────────────────────────────────────┘
```

## Database Schema

```
UserNotification (notification rules)
├── notification_id (PK)
├── user_id (FK → User)
├── site_id (FK → Site)
├── metric (e.g., "XC0", "XC10")
├── comparison ("gt", "gte", "lt", "lte", "eq")
├── threshold (0-100 percentage)
├── lead_time_hours (0-168)
├── improvement_threshold (default 15%)
├── active (boolean)
└── last_triggered_at

PushSubscription (browser push endpoints)
├── subscription_id (PK)
├── user_id (FK → User)
├── endpoint (unique, Web Push URL)
├── p256dh (ECDH public key)
├── auth (authentication token)
└── is_active

NotificationEvent (audit log)
├── event_id (PK)
├── notification_id (FK → UserNotification)
├── subscription_id (FK → PushSubscription)
├── triggered_at
├── payload (JSON)
└── delivery_status

NotifiedForecast (state tracking)
├── id (PK)
├── notification_id (FK → UserNotification)
├── forecast_date
├── last_value
├── last_event_type
└── notified_at
└── UNIQUE(notification_id, forecast_date)
```

## Consequences

### Positive

- **Reliable delivery**: 30-minute polling ensures notifications arrive within 30 minutes of forecast availability
- **No spam**: State tracking prevents duplicate notifications for unchanged forecasts
- **Meaningful updates**: Users are notified of deterioration and significant improvements, not just initial threshold crossings
- **Auditable**: NotificationEvent table provides complete history for debugging and user transparency
- **Scalable**: Bulk fetching of predictions and subscriptions minimizes database queries

### Negative

- **Latency**: Up to 30-minute delay between forecast availability and notification
- **Resource usage**: Continuous polling even when no new forecasts exist
- **Complexity**: State machine logic adds cognitive overhead for maintenance

### Alternatives Considered

1. **Event-driven triggers**: Trigger notifications directly from forecast pipeline. Rejected due to coupling concerns and difficulty handling retries/failures.

2. **Webhook from forecast source**: Not available from GFS/NOAA infrastructure.

3. **Shorter polling interval**: 5-10 minutes would reduce latency but increase load with minimal user benefit.

## Related Files

| Component | Path |
|-----------|------|
| Models | `backend/app/models.py` |
| Evaluation logic | `backend/app/services/notifications.py` |
| Push delivery | `backend/app/services/push_delivery.py` |
| Celery tasks | `backend/app/celery_app.py` |
| API routes | `backend/app/routers/notifications.py` |
| CRUD operations | `backend/app/crud.py` |
| Tests | `backend/tests/test_notifications.py` |
