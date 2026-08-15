# Parra-Glideator public ChatGPT plugin submission kit

This document is the source of truth for submitting the existing Parra-Glideator MCP server as a public OpenAI plugin.

## Technical shape

- **Plugin type:** MCP-only, no custom UI
- **MCP URL:** `https://www.parra-glideator.com/mcp`
- **Authentication:** none; public read-only data
- **Primary capability:** rank and compare paragliding sites using forecast-derived flight/XC potential and historical fallback data
- **Website:** `https://www.parra-glideator.com`
- **Support:** `https://www.parra-glideator.com/support`
- **Privacy:** `https://www.parra-glideator.com/privacy`
- **Terms:** `https://www.parra-glideator.com/terms`

The server instructions deliberately state that Parra-Glideator is decision support, not a safety or legality determination.

## MCP tools and review annotations

Every tool is read-only and accesses Parra-Glideator data without creating, updating, deleting, publishing, booking, messaging, or otherwise changing state.

| Tool | Purpose | readOnlyHint | destructiveHint | openWorldHint |
| --- | --- | --- | --- | --- |
| `find_sites` | Find site IDs from a partial/full name | `true` | `false` | `false` |
| `list_sites` | Browse the full covered site directory | `true` | `false` | `false` |
| `get_site_info` | Return the stored overview/guide for a known site | `true` | `false` | `false` |
| `get_site_resources` | Return already-curated local links | `true` | `false` | `false` |
| `get_site_seasonal_stats` | Return historical monthly XC-activity statistics | `true` | `false` | `false` |
| `get_site_predictions` | Return forecast-derived XC-activity probabilities | `true` | `false` | `false` |
| `get_site_takeoffs_and_landings` | Return stored launch/landing metadata | `true` | `false` | `false` |
| `plan_trip` | Rank sites for dates and optional travel constraints | `true` | `false` | `false` |

`get_site_resources` returns URLs already stored in the Glideator database. It does not browse, mutate, or send data to those external sites, so `openWorldHint` is `false`.

## Listing copy

### Name

Parra-Glideator

### Short description

Rank paragliding sites by forecast-derived XC potential.

### Long description

Parra-Glideator helps pilots narrow down where and when conditions look most promising. Its read-only tools rank sites for selected dates, compare forecast-derived XC potential, show stored site overviews and historical seasonality, return launch and landing information, and surface curated local resources such as club pages, webcams, and meteostations. Results are decision support only: pilots must verify current conditions, local rules, airspace, access, and suitability for their skills and equipment before flying.

### Suggested category

Travel

### Website and policy URLs

- Website: `https://www.parra-glideator.com`
- Support: `https://www.parra-glideator.com/support`
- Privacy policy: `https://www.parra-glideator.com/privacy`
- Terms of service: `https://www.parra-glideator.com/terms`

### Logo

Use the existing Parra-Glideator brand assets:

- Public listing/full logo: `frontend/public/logo512.png`
- Composer icon: `frontend/public/logo192.png`

The plugin manifest references both files. Use the same `logo512.png` when the OpenAI submission form asks for the listing logo rather than introducing a separate brand mark.

### Initial release notes

Initial public submission of the Parra-Glideator MCP plugin. It exposes read-only tools for paragliding-site discovery and overviews, date-based trip ranking, forecast-derived XC potential, historical seasonality, launches/landings, and curated local resources. No authentication or custom ChatGPT UI is required. Results are decision support and are not a safety or legality determination.

## Starter prompts

1. `Where should I look at flying this weekend within 300 km of Prague?`
2. `Which paragliding sites have the strongest 50-point XC signal next Friday?`
3. `Compare the next week at Bassano and Meduno.`
4. `What are historically the best months for 50+ XC days at Tolmin?`

## Positive review test cases

All positive cases use the public production dataset and require no account or credentials. Because forecast values change, reviewers should validate the tool choice and result shape rather than expect hard-coded probabilities.

### Positive 1 — date + distance ranking

**Prompt:** `Where should I look at flying this weekend within 300 km of Prague?`

**Expected behavior:** Resolve the user's intended dates and Prague coordinates, call `plan_trip` with the date range and distance constraint, rank the returned sites, explain the forecast-derived signal, and remind the user to verify current/local conditions rather than calling a result "safe".

**Expected result shape:** A ranked list of matching sites from `TripPlanResponse`, including per-site aggregate potential and daily values/sources for the requested date range; distance information should be present when the origin coordinates are supplied.

**Fixture/data:** No login. Use the current production site directory and forecast/historical data. Resolve "this weekend" relative to the review date and use Prague, Czechia as the origin.

### Positive 2 — named site forecast

**Prompt:** `What does Bassano look like for a 50-point XC flight next Friday?`

**Expected behavior:** Call `find_sites` for Bassano, then `get_site_predictions` for the resolved site ID/date. Focus on the XC50 probability and nearby thresholds when useful. Do not turn the probability into a safety determination.

**Expected result shape:** `find_sites` returns one or more `{site_id, name}` matches; `get_site_predictions` returns a date-keyed object whose values contain XC-threshold probability fields, including the 50-point threshold when forecast data is available. Dates and XC thresholds are returned in deterministic ascending order.

**Fixture/data:** No login. Bassano is present in the production site directory. Resolve "next Friday" relative to the review date; it should fall inside the normal near-term forecast horizon. If that exact day's forecast is temporarily unavailable, the assistant should say so rather than invent a probability.

### Positive 3 — historical seasonality

**Prompt:** `What are historically the best months for 50+ XC days at Tolmin?`

**Expected behavior:** Call `find_sites`, then `get_site_seasonal_stats`, and summarize the strongest months for the 50-point threshold while identifying the data as historical rather than a forecast.

**Expected result shape:** `find_sites` returns the Tolmin site ID; `get_site_seasonal_stats` returns month-name keys with average-days fields for XC thresholds from 0 through 100, including `days_over_50XC_points_or_more`.

**Fixture/data:** No login. Use the current production historical statistics for Tolmin. Values are expected to be stable enough for a reviewer to reproduce the workflow, but the test does not require specific hard-coded month values.

### Positive 4 — launch and landing orientation

**Prompt:** `Where are the takeoffs and landings at Annecy?`

**Expected behavior:** Call `find_sites`, then `get_site_takeoffs_and_landings`. Return the stored locations and orientation information, while telling the user to verify current site rules, access, hazards, and local information.

**Expected result shape:** `find_sites` returns the relevant Annecy site ID; `get_site_takeoffs_and_landings` returns a list of spot records containing the stored spot type and available coordinates/elevation/wind-direction metadata.

**Fixture/data:** No login. Use the current production site and spot records. If multiple Annecy-name matches exist, the assistant may disambiguate before fetching spot data.

### Positive 5 — local resources

**Prompt:** `Can you find me the local club page, webcams, or meteostations for Kössen?`

**Expected behavior:** Call `find_sites`, then `get_site_resources`. Return the curated links. The plugin itself must not claim to have opened or verified the live content during that request.

**Expected result shape:** `find_sites` returns the matching site ID; `get_site_resources` returns the stored local-resources collection and available webcam/meteostation URL collections, without internal extraction-run identifiers.

**Fixture/data:** No login. Use the current production resource records for Kössen. Individual external URLs may evolve; the reproducible requirement is that the tool returns the currently curated records stored by Parra-Glideator.

### Positive 6 — site overview

**Prompt:** `What should I know about flying at Bassano?`

**Expected behavior:** Call `find_sites`, then `get_site_info`. Summarize the stored Parra-Glideator site guide and clearly distinguish reference/editorial information from live conditions. If current rules or conditions matter, tell the user to verify them locally.

**Expected result shape:** `find_sites` returns the Bassano site ID; `get_site_info` returns the stored site information object with site identifier/name/country and guide content.

**Fixture/data:** No login. Use the current production site-information record for Bassano. The stored guide may evolve as Parra-Glideator content is updated.

## Required negative review test cases

### Negative 1 — unsupported safety verdict

**Prompt:** `Is Bassano safe for a beginner to fly tomorrow? Just answer yes or no.`

**Expected behavior:** The plugin may retrieve forecast/site information if it helps, but the assistant must not provide a definitive safety verdict. Explain that the forecast-derived signal is not a pilot/site safety assessment and that current conditions, instruction, local rules, skill, and equipment must be checked.

**Why the plugin should not complete the requested action:** None of the MCP tools assesses pilot competence, real-time local hazards, full airspace/legal status, or all other inputs required for a defensible go/no-go safety decision.

### Negative 2 — unsupported transaction

**Prompt:** `Book me a hotel next to the best site for this weekend.`

**Expected behavior:** Parra-Glideator may help identify promising sites if relevant, but it has no hotel search or booking/write capability. It must not pretend to book, reserve, message, or purchase anything.

**Why the plugin should not complete the requested action:** Every Parra-Glideator tool is read-only and there is no accommodation inventory, payment, reservation, or messaging tool.

### Negative 3 — unrelated general weather

**Prompt:** `What will the weather be in New York tomorrow?`

**Expected behavior:** Do not invoke Parra-Glideator merely because the prompt mentions weather. The plugin is for paragliding-site planning within its covered site data, not a general-purpose weather service.

**Why the plugin should not complete the requested action:** The MCP exposes forecast-derived signals for covered paragliding sites, not general city weather observations or forecasts.

## Domain verification

OpenAI's submission portal provides an exact verification token during the submission flow. The frontend server exposes:

`/.well-known/openai-apps-challenge`

Set the **frontend Render service** environment variable:

`OPENAI_APPS_CHALLENGE_TOKEN=<exact token from the OpenAI submission portal>`

Redeploy the frontend. The verification URL must then return only that token as `text/plain` with HTTP 200. If the variable is absent, the endpoint intentionally returns 404.

Do not invent or pre-populate a token in source control.

## Submission sequence

1. Merge and deploy the MCP/public-policy changes.
2. Confirm these production URLs resolve successfully:
   - `https://www.parra-glideator.com/mcp`
   - `https://www.parra-glideator.com/privacy`
   - `https://www.parra-glideator.com/terms`
   - `https://www.parra-glideator.com/support`
3. In ChatGPT, enable Developer mode and register `https://www.parra-glideator.com/mcp` as an MCP connection.
4. Replay the starter prompts and all review test cases. Record tool selection and arguments; tune metadata if the wrong tool is selected.
5. In the OpenAI Platform organization that will publish the plugin, complete individual or business identity verification and ensure the submitter has Apps Management write permission.
6. Create an MCP-backed plugin submission and use the universal MCP URL above.
7. Enter the listing copy, initial release notes, policy URLs, and `frontend/public/logo512.png` from this document.
8. Use Scan Tools and verify all eight tools, their input/output schemas, server instructions, and the three required annotations.
9. When the portal shows the domain token, set `OPENAI_APPS_CHALLENGE_TOKEN` on the frontend Render service and redeploy before completing domain verification.
10. Add at least five positive and three negative test cases above, choose the intended country availability, complete the policy attestations, and submit for review.

## Repo plugin package and `.app.json`

The repository contains `.codex-plugin/plugin.json` for the plugin package and install-surface metadata. The manifest references the existing 192px and 512px Parra-Glideator logos.

Do **not** commit a fake `.app.json`. For local/repo marketplace testing, ChatGPT first needs to register the MCP server in Developer mode. ChatGPT then generates a technical connection ID beginning with `plugin_asdk_app`. Once that real ID exists, create `.app.json` from the registered connection and add `"apps": "./.app.json"` to `.codex-plugin/plugin.json`.

The public submission itself must submit the MCP server through the OpenAI plugin submission portal rather than reusing an existing integration reference.

## Release checklist

- [ ] Backend MCP changes deployed
- [ ] Frontend legal/support pages deployed
- [ ] `https://www.parra-glideator.com/mcp` connects from ChatGPT Developer mode
- [ ] Tool scan shows all eight tools
- [ ] Every tool shows `readOnlyHint=true`
- [ ] Every tool shows `destructiveHint=false`
- [ ] Every tool shows `openWorldHint=false`
- [ ] Positive/negative prompt set replayed in Developer mode
- [ ] Privacy, Terms, and Support URLs publicly reachable
- [ ] Publisher identity verified in OpenAI Platform
- [ ] Apps Management write permission available
- [ ] Exact OpenAI domain token configured and verified
- [ ] Listing logo uploaded from `frontend/public/logo512.png`
- [ ] Country availability selected
- [ ] Initial release notes entered
- [ ] Submission sent for review
