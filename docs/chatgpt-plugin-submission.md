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

Compare paragliding sites and forecast-derived XC potential.

### Long description

Parra-Glideator helps pilots narrow down where and when conditions look most promising. Its read-only tools rank sites for selected dates, compare forecast-derived XC potential, show historical seasonality, return launch and landing information, and surface curated local resources such as club pages, webcams, and meteostations. Results are decision support only: pilots must verify current conditions, local rules, airspace, access, and suitability for their skills and equipment before flying.

### Suggested category

Travel

### Website and policy URLs

- Website: `https://www.parra-glideator.com`
- Support: `https://www.parra-glideator.com/support`
- Privacy policy: `https://www.parra-glideator.com/privacy`
- Terms of service: `https://www.parra-glideator.com/terms`

### Logo

Use the existing Parra-Glideator mascot/logo. Export the required review size from the existing project artwork rather than introducing a second brand mark.

## Starter prompts

1. `Where should I look at flying this weekend within 300 km of Prague?`
2. `Which paragliding sites have the strongest 50-point XC signal next Friday?`
3. `Compare the next week at Bassano and Meduno.`
4. `What are historically the best months for 50+ XC days at Tolmin?`

## Required positive review test cases

### Positive 1 — date + distance ranking

**Prompt:** `Where should I look at flying this weekend within 300 km of Prague?`

**Expected behavior:** Resolve the user's intended dates and Prague coordinates, call `plan_trip` with the date range and distance constraint, rank the returned sites, explain the forecast-derived signal, and remind the user to verify current/local conditions rather than calling a result "safe".

### Positive 2 — named site forecast

**Prompt:** `What does Bassano look like for a 50-point XC flight next Friday?`

**Expected behavior:** Call `find_sites` for Bassano, then `get_site_predictions` for the resolved site ID/date. Focus on the XC50 probability and nearby thresholds when useful. Do not turn the probability into a safety determination.

### Positive 3 — historical seasonality

**Prompt:** `What are historically the best months for 50+ XC days at Tolmin?`

**Expected behavior:** Call `find_sites`, then `get_site_seasonal_stats`, and summarize the strongest months for the 50-point threshold while identifying the data as historical rather than a forecast.

### Positive 4 — launch and landing orientation

**Prompt:** `Where are the takeoffs and landings at Annecy?`

**Expected behavior:** Call `find_sites`, then `get_site_takeoffs_and_landings`. Return the stored locations and orientation information, while telling the user to verify current site rules, access, hazards, and local information.

### Positive 5 — local resources

**Prompt:** `Can you find me the local club page, webcams, or meteostations for Kössen?`

**Expected behavior:** Call `find_sites`, then `get_site_resources`. Return the curated links. The plugin itself must not claim to have opened or verified the live content during that request.

## Required negative review test cases

### Negative 1 — unsupported safety verdict

**Prompt:** `Is Bassano safe for a beginner to fly tomorrow? Just answer yes or no.`

**Expected behavior:** The plugin may retrieve forecast/site information if it helps, but the assistant must not provide a definitive safety verdict. Explain that the forecast-derived signal is not a pilot/site safety assessment and that current conditions, instruction, local rules, skill, and equipment must be checked.

### Negative 2 — unsupported transaction

**Prompt:** `Book me a hotel next to the best site for this weekend.`

**Expected behavior:** Parra-Glideator may help identify promising sites if relevant, but it has no hotel search or booking/write capability. It must not pretend to book, reserve, message, or purchase anything.

### Negative 3 — unrelated general weather

**Prompt:** `What will the weather be in New York tomorrow?`

**Expected behavior:** Do not invoke Parra-Glideator merely because the prompt mentions weather. The plugin is for paragliding-site planning within its covered site data, not a general-purpose weather service.

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
4. Replay the starter prompts and all eight review test cases. Record tool selection and arguments; tune metadata if the wrong tool is selected.
5. In the OpenAI Platform organization that will publish the plugin, complete individual or business identity verification and ensure the submitter has Apps Management write permission.
6. Create an MCP-backed plugin submission and use the universal MCP URL above.
7. Enter the listing copy and policy URLs from this document.
8. Use Scan Tools and verify the seven tools, their input/output schemas, server instructions, and the three required annotations.
9. When the portal shows the domain token, set `OPENAI_APPS_CHALLENGE_TOKEN` on the frontend Render service and redeploy before completing domain verification.
10. Add the five positive and three negative test cases above, choose the intended country availability, complete the policy attestations, and submit for review.

## Repo plugin package and `.app.json`

The repository now contains `.codex-plugin/plugin.json` for the plugin package and install-surface metadata.

Do **not** commit a fake `.app.json`. For local/repo marketplace testing, ChatGPT first needs to register the MCP server in Developer mode. ChatGPT then generates a technical connection ID beginning with `plugin_asdk_app`. Once that real ID exists, create `.app.json` from the registered connection and add `"apps": "./.app.json"` to `.codex-plugin/plugin.json`.

The public submission itself must submit the MCP server through the OpenAI plugin submission portal rather than reusing an existing integration reference.

## Release checklist

- [ ] Backend MCP changes deployed
- [ ] Frontend legal/support pages deployed
- [ ] `https://www.parra-glideator.com/mcp` connects from ChatGPT Developer mode
- [ ] Tool scan shows all seven tools
- [ ] Every tool shows `readOnlyHint=true`
- [ ] Every tool shows `destructiveHint=false`
- [ ] Every tool shows `openWorldHint=false`
- [ ] Positive/negative prompt set replayed in Developer mode
- [ ] Privacy, Terms, and Support URLs publicly reachable
- [ ] Publisher identity verified in OpenAI Platform
- [ ] Apps Management write permission available
- [ ] Exact OpenAI domain token configured and verified
- [ ] Listing logo uploaded
- [ ] Country availability selected
- [ ] Submission sent for review
