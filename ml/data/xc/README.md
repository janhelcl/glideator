# XC static experiment inputs

## Jev production site context

`jev_site_context_prod_2026-09-21.json` is a frozen read-only export from the production Render database:

- database: `glideator-db`;
- tables: `public.sites` and `public.spots`;
- site scope: `site_id <= 250`;
- takeoff scope: `lower(type) = 'takeoff'`;
- captured: 2026-09-21;
- records: 248 sites and 535 takeoffs.

The raw/full analytics spots relation is not used. The snapshot supplies the exact production site name and every production takeoff, including its stored wind-direction range, coordinates and altitude.

The Jev runner validates the schema, requires named sites and takeoffs with wind directions, checks that every evaluation site is present, and fingerprints the canonical JSON into its cache manifest. Refreshing this file is a new context version and must use a new output directory or an explicitly cleared cache.
