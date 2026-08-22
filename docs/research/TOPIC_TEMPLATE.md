# <topic>

## Goal / endpoint
<Concrete user outcome or failure being investigated. Define the practical endpoint, not a transient error message.>

## Current state
<Concise present state of the endpoint and the main unresolved question.>

## Research history

### Searches tried
Record only meaningful exact or near-exact searches. Do not reconstruct historical queries that were not actually recorded.

- `<query>` — <useful / no applicable result / led to source>

### Useful findings
- <finding> — <source/reference and why it matters>

### Research routes ruled out / weak
- <route> — <why it was rejected, incompatible, stale, or insufficient>

## Endpoint debugging / failure history
Use this section for practical endpoint failures, especially once the same endpoint has failed through three or more materially distinct routes. Do **not** log every syntax error, typo, transient test failure, or routine edit. Preserve debugging steps when they establish reusable information about the endpoint, an integration boundary, tool/runtime behavior, or why a plausible route should not be repeated.

### Route / debugging step — <short name>
**What was tried:**
<Architecture, integration route, or meaningful debugging step.>

**Observed endpoint result:**
<What happened to the practical user outcome.>

**What this established:**
<Decisive evidence or lesson. Include a few relevant debugging steps when they would save a future agent from rediscovering the same information.>

**Reusable lesson:**
<How this should influence future implementation or testing.>

**Disposition:** <active / superseded / ruled out / worth revisiting only if ...>

Repeat for materially different routes. When several iterations are the same route and add the same conclusion, consolidate them into one entry while preserving distinct evidence that would help a future agent recognize or avoid the failed approach.

## Current preferred route / current unknown
<Best presently supported route and unresolved unknowns.>

## Re-search / retry triggers
Search or retry only if prior evidence is stale/incomplete, a materially new failure changes the question, a distinct route is being considered, materially new evidence makes a previously failed route plausible, or the user explicitly asks for fresh/broader research.

## Sources / durable references
<List only useful sources/references. Do not copy large source contents.>
