# Deployed Application Security Audit

Date: 2026-08-18  
Last updated: 2026-08-20
Branch: `feat_CSP`  
Status: Security Pass 0 complete; Security Pass 1 implemented and locally verified; broader programme paused before Pass 2

## Executive summary

No critical compromise, secret exposure, production debugger, external runtime
CDN dependency, or known vulnerable application dependency was identified.

The most important findings are:

1. The public numerical callback is an unauthenticated CPU and memory workload.
   The repository declares Gunicorn's default single synchronous worker; a
   Railway command override remains a build-log verification item. Input
   bounds are useful, but there is no evidenced request-rate control or
   application request-body cap. Local callback measurements were CPU-bound and
   exposed a legitimate
   2.11 MB Dash state round-trip, so neither a body cap nor a rate threshold
   should be guessed from the approximately 2 KB simulation-run request alone.
   Availability is the clearest current security risk.
2. A restrictive CSP is feasible, but it cannot be added as a simple static
   `script-src 'self'` header. Dash emits three executable inline scripts and
   the Cloudflare production path injects a fourth, changing inline JavaScript
   Detections bootstrap. JavaScript Detections is now confirmed enabled, not an
   unexplained injection. Dash hashes can cover the application scripts;
   Cloudflare's documented nonce propagation should cover the edge injection.
   Runtime Dash and MathJax CSS still requires an inline-style allowance.
3. Production has `FORCE_HTTPS=true`, and Pass 1 now uses that verified
   production boundary to enable Flask `TRUSTED_HOSTS` for the apex, `www`, and
   generated Railway hostname. Local HTTP development leaves host enforcement
   off. The first-value `X-Forwarded-Proto` behavior is unchanged, regression
   tested, and no `ProxyFix` middleware was added.
4. Public HTTP already redirects to HTTPS even though Cloudflare's **Always Use
   HTTPS** setting is off. Both the Cloudflare and direct Railway hostnames show
   the same pre-Flask Railway redirect. Cloudflare Always Use HTTPS would
   duplicate the current public result while making edge ownership explicit;
   it is not required to obtain a redirect today. HSTS remains absent.
5. The Railway-generated hostname is confirmed public. It bypasses Cloudflare's
   scanner rule, Bot Fight Mode, JavaScript Detections, and any future
   Cloudflare-only callback rate limit. This is an architecture trade-off, not
   automatically a vulnerability: it may be retained as a diagnostic/fallback
   ingress only if application-level controls are treated as the security
   baseline.
6. **Do not move the current Railway/Cloudflare architecture to Full (strict)
   merely because the browser-facing certificate is valid.** Railway's current
   documentation explicitly instructs Cloudflare-proxied custom domains to use
   Full and says Full (strict) will not work as intended when Railway presents
   its default `*.up.railway.app` certificate. Full (strict) should be revisited
   only if the actual origin certificate/SNI path is verified and Railway
   confirms support for this domain arrangement.

The recommended CSP target is a staged, release-coupled application policy with
report-only and enforce modes, Dash-generated hashes, a per-response nonce for
Cloudflare injection compatibility, same-origin runtime sources, and
`style-src 'unsafe-inline'` as a documented initial limitation. No evidence from
the local enforcement test justified `script-src 'unsafe-inline'` or
`'unsafe-eval'`.

## Audit scope and evidence

### Repository evidence reviewed

- `pendulum_app.py`
- `app/config.py`
- `app/server_hooks.py`
- route, page, component, callback, serialization, validation, and model code
- `assets/custom-header.html`
- all first-party JavaScript and CSS assets
- the vendored MathJax 3.2.0 entry point, fonts, and licence
- `pyproject.toml`, `uv.lock`, `.python-version`, and `Procfile`
- HTTP, MathJax, routing, callback, and server-hook tests
- the required top-level project and production documentation

### Reference implementation reviewed

The separate `population-dynamics` repository was inspected read-only. The most
relevant completed patterns were:

- `off`, `report-only`, and `enforce` CSP modes;
- a dedicated CSP builder with validated Dash hashes;
- calling `app.csp_hashes()` only after clientside callbacks are registered;
- an accepted, explicit `style-src 'unsafe-inline'` compatibility limitation;
- locally served MathJax and fonts;
- `TRUSTED_HOSTS`, conservative browser headers, and regression tests;
- optional Cloudflare-injected origin-secret validation; and
- a clear separation between application response controls and edge controls.

Those patterns are useful, but they are not copied as conclusions. This app has
a different Canvas renderer, a different callback workload, Railway rather than
the reference deployment baseline, and a confirmed Cloudflare JavaScript
Detections injection that requires extra CSP handling.

### Live production evidence collected

Read-only checks were performed against:

- `https://double-pendulum.net/`
- `https://double-pendulum.net/simulation`
- `https://double-pendulum.net/equations`
- `https://www.double-pendulum.net/`
- representative Dash runtime and vendored MathJax asset URLs

Confirmed on 2026-08-18:

- apex and `www` HTTPS routes returned the Dash application;
- apex and `www` HTTP requests returned `301` to the same hostname over HTTPS;
- HTML responses had `nosniff`, `SAMEORIGIN`, and
  `strict-origin-when-cross-origin` but no CSP or HSTS;
- the local MathJax JavaScript and a representative local MathJax font returned
  `200` from the application origin;
- Dash debug UI and property checks were disabled in the emitted config;
- `/_reload-hash` returned `reloadHash: null`;
- every runtime script, stylesheet, image, and font observed for the Equations
  page was same-origin;
- Cloudflare injected `/cdn-cgi/challenge-platform/scripts/jsd/main.js` through
  a changing inline bootstrap; JavaScript Detections is confirmed enabled; and
- TLS 1.2 and TLS 1.3 handshakes to the Cloudflare edge succeeded. The minimum
  accepted edge TLS version was not established by this audit.

### Verified Security Pass 0 deployment facts

The following production facts were verified manually in the Railway and
Cloudflare control planes and are no longer assumptions:

- Railway production variables contain only `FORCE_HTTPS=true`; no explicit
  Flask/Dash debug or environment variable is configured.
- Railway Networking exposes `double-pendulum.net`,
  `www.double-pendulum.net`, and
  `web-production-65a59.up.railway.app`.
- No Railway health-check path is configured.
- The Railway-generated hostname is publicly reachable and returns the same
  application directly, without traversing Cloudflare.
- Cloudflare uses **Full (automatic)**, with **Always Use HTTPS** and HSTS off.
- Cloudflare Bot Fight Mode and JavaScript Detections are on. The existing
  scanner-blocking custom rule remains active.

Additional read-only ingress checks on 2026-08-18 established:

- HTTP requests to both `double-pendulum.net` and the Railway-generated
  hostname returned an empty `301` with `x-railway-67: 67` and no
  Flask-added security headers. The redirect therefore occurs at Railway's
  public edge before the current Flask hooks execute.
- Supplying `X-Forwarded-Proto: https` on either HTTP ingress did not suppress
  that Railway redirect.
- Supplying `X-Forwarded-Proto: http`, `http, https`, or `https, http` on an
  HTTPS request to the direct Railway hostname still returned the application
  with `200`; `X-Forwarded-Proto: http` on Cloudflare HTTPS did the same.
  Because the Flask hook would redirect if it received a first value of
  `http`, this is black-box evidence that Railway replaces or otherwise
  normalizes the external protocol signal before Flask evaluates it.
- No same-URL HTTPS redirect loop was observed, and an external client could
  neither bypass the Railway HTTP redirect nor induce a loop by supplying the
  protocol header. This establishes present behavior, not a general licence to
  trust arbitrary proxy headers or hop counts.

The direct Railway HTTPS response also contained the same `nosniff`, framing,
and referrer headers as the Cloudflare response. Together with the matching
Flask hook values, this confirms those three controls originate in the
application rather than Cloudflare.

### Security Pass 0 callback measurements

Measurements used the locked local Python 3.12 environment, Flask's test
client, and the real `POST /_dash-update-component` callback envelope. Sizes
are compact, uncompressed JSON bytes. Wall and process CPU time cover model
construction, integration, Canvas payload construction/validation, Dash JSON
serialization, and the Flask callback response. They are local evidence, not
Railway capacity measurements.

| Valid case | Samples | Request | Response | Wall | CPU |
| --- | ---: | ---: | ---: | ---: | ---: |
| Default controls, unity parameters, simple Lagrangian, first run | 4,000 | 2,005 B | 215,315 B | 2.184 s | 2.163 s |
| Same default after caches were warm | 4,000 | 2,006 B | 215,320 B | 0.058 s | 0.058 s |
| Moderate simple Lagrangian, 30 s | 6,000 | 2,011 B | 1,042,306 B | 0.191 s | 0.190 s |
| Moderate simple Hamiltonian, 30 s | 6,000 | 2,012 B | 814,959 B | 0.493 s | 0.491 s |
| Moderate compound Lagrangian, 30 s, first compound path | 6,000 | 2,013 B | 1,048,026 B | 2.250 s | 2.245 s |
| Moderate compound Hamiltonian, 30 s | 6,000 | 2,014 B | 820,827 B | 0.520 s | 0.519 s |
| Moderate simple Lagrangian, strict solver, 30 s | 6,000 | 2,013 B | 1,042,371 B | 0.251 s | 0.250 s |
| Boundary-envelope simple Lagrangian, strict solver, 60 s | 12,000 | 2,029 B | 2,101,398 B | 1.092 s | 1.090 s |
| Boundary-envelope simple Hamiltonian, strict solver, 60 s | 12,000 | 2,030 B | 1,652,874 B | 1.390 s | 1.387 s |
| Boundary-envelope compound Lagrangian, 60 s | 12,000 | 2,029 B | 2,113,053 B | 0.373 s | 0.372 s |
| Boundary-envelope compound Hamiltonian, 60 s | 12,000 | 2,031 B | 1,667,091 B | 0.399 s | 0.399 s |

The moderate case used non-zero angles and angular velocities. The
boundary-envelope cases used the maximum 60-second duration, maximum angular
velocity magnitudes, boundary angles, minimum lengths, a large mass ratio, and
maximum gravity accepted by the current validator. This deliberately samples a
high-cost valid envelope; it is not proof of the absolute worst trajectory in
a continuous input space.

Wall and CPU time were nearly identical, so the measured callback work is
CPU-bound. First-use symbolic/model cache effects were material: the first
default simple Lagrangian and first compound Lagrangian paths each took about
2.2 seconds, while the repeated default took 0.058 seconds. The largest
measured response was about 2.11 MB. All cases completed below Gunicorn's
30-second default timeout locally, but Railway CPU, memory, cold-start cost,
network transfer, and concurrent queueing remain unmeasured.

A second legitimate Dash request is important for body-limit planning. When a
setting changes, `mark_output_stale_on_input_change()` sends the current Canvas
store back to the same Dash endpoint as callback `State`. Using the largest
measured valid payload produced a 2,112,330-byte request and a 2,113,430-byte
response in 0.228 seconds. Therefore a global `MAX_CONTENT_LENGTH` based on the
approximately 2 KB run request would break valid interaction. No body-size cap
or rate threshold is proposed from these measurements alone.

### Security Pass 0 deployment/build evidence

Repository-controlled deployment intent is clear:

- `.python-version` selects Python 3.12 and `pyproject.toml` constrains the
  runtime to Python 3.12.
- `Procfile` declares `web: gunicorn pendulum_app:server`.
- runtime dependencies are declared in `pyproject.toml`; `uv.lock` contains
  exact registry versions and artifact hashes.
- there is no Dockerfile, `railway.toml`/`railway.json`, Railpack/Nixpacks
  configuration, active root requirements file, or repository CI deployment
  workflow. The old freeze below `legacy/` is not an active build input.
- live Dash and Plotly versions and the emitted Python version matched the
  committed locked/runtime state during this audit.

Railway currently documents Railpack as its default source builder and Railpack
documents that a Python project containing `pyproject.toml` and `uv.lock` uses
the uv package-manager path. Railpack also documents automatic root `Procfile`
detection and gives the `web` process highest priority. Therefore the
repository-default build/start model is Railpack + uv, followed by
`gunicorn pendulum_app:server` from the Procfile. Production behavior is
consistent with that model. Railpack currently labels Procfile support
deprecated in favor of native start-command configuration, but still documents
automatic detection; this is deployment-maintenance evidence, not a present
security defect or a reason to change strategy during the audit.

That is still not proof of this service's actual build. A Railway service-level
custom install/build/start command can override repository detection, and no
build log or service Build/Deploy settings export was available in this pass.
It remains externally unverified whether the deployed service used Railpack,
the exact uv install flags, whether the dev group was excluded, and whether the
Procfile command was unmodified. Confirm those items from the next production
build log and Railway Build/Deploy settings; do not infer them from matching
live package versions alone.

### Point-in-time scanner evidence

- Bandit scanned 5,393 lines under `app/`, `src/`, and `pendulum_app.py` and
  reported no issues at any severity.
- `pip-audit` against the installed project environment found no advisory for
  an application dependency. It did report `PYSEC-2026-196` for the local
  environment's `pip==26.1.1`; `pip` is not a project dependency in `uv.lock`
  and the reported fixed version is 26.1.2.
- An OSV query for the separately vendored npm package `mathjax==3.2.0`
  returned no known advisory.
- No tracked `.env`, key, IDE, virtual-environment, or bytecode artifact was
  found. A credential-pattern scan found no credential; JavaScript variables
  named `loopToken` were ordinary renderer state.

These scans are dated evidence, not a claim that future advisories cannot be
published.

### Local CSP compatibility probe

A temporary local server was run with a candidate policy containing:

- same-origin scripts and resources;
- all three values returned by `app.csp_hashes()`;
- no unsafe script or eval source;
- same-origin fonts and connections;
- `data:` only for images; and
- a temporary inline-style allowance.

The Equations page rendered 57 MathJax containers, the Simulation page created
all three Canvas views, a simulation callback completed, and the browser
reported no CSP errors. This is strong feasibility evidence, but it does not
replace a production report-only period because the local test did not include
Cloudflare's injected script.

The exact temporary process was stopped and port 8063 was confirmed closed.

### Security Pass 1 implementation evidence

Security Pass 1 was implemented on 2026-08-20 without changing CSP,
Cloudflare, Railway, HTTPS redirect logic, proxy middleware, HSTS, request-size
limits, rate limiting, Canvas state, Gunicorn, dependencies, or MathJax.

Implemented controls:

- `FORCE_HTTPS=true`, the verified production deployment boundary, enables
  Flask `TRUSTED_HOSTS` for `double-pendulum.net`,
  `www.double-pendulum.net`, and
  `web-production-65a59.up.railway.app`. With `FORCE_HTTPS=false`, trusted-host
  enforcement remains off so localhost development and ordinary tests are not
  coupled to production hostnames.
- Flask responses now include
  `Permissions-Policy: camera=(), microphone=(), geolocation=()` alongside the
  existing browser headers.
- Simulation validation explicitly permits only the supported model,
  formulation, and named integrator-policy strings. A missing integrator policy
  remains an intentional safe request for the server default; unknown strings
  are rejected.
- Finite-number checks now cover start/end time, all four initial-state values,
  lengths, the active simple/compound masses, and gravity. Boolean values are
  not accepted as numbers. Parameter-stepper callback state also rejects
  boolean and non-finite values before rounding.
- Solver-setup, metadata-conversion, and output-preparation exceptions are
  logged server-side with run/model/formulation context. Failed Canvas payloads
  contain stable messages rather than `str(exc)`. Deliberate solver metadata
  remains available as educational diagnostics.
- Every application link that opens a new tab now explicitly uses
  `rel="noopener noreferrer"`.

Focused regression coverage verifies the three production hosts, hostile-host
rejection, localhost behavior, the existing redirect cases, first forwarded
protocol selection, secure requests with a conflicting forwarded value, the
new header, all enum classes, representative non-finite values across every
numeric input category, stepper state, exception redaction/logging, and link
attributes. The implementation-time full suite passed: **227 tests passed in
8.23 seconds**.
A production-mode import smoke check returned `200` for the apex and direct
Railway hosts, `400` for a hostile host, and the expected Permissions Policy.

Production deployment verification remains required before Pass 2: exercise
all three allowed hosts through their intended ingress paths and confirm that
the generated Railway hostname has not changed. If the deployment stops using
`FORCE_HTTPS=true`, or the host inventory changes, the trusted-host boundary
must be revised deliberately rather than silently broadening the allowlist.

### Security branch closeout and promotion readiness

The broader hardening programme is paused after Pass 1. Passes 2–4 are paused,
not abandoned; no CSP scaffolding, report-only policy, or enforcement work has
been implemented. The Pass 0 evidence and deferred findings remain in this
branch-local document so that a future security pass can resume without
repeating the investigation unnecessarily.

The Pass 1 application changes are cleanly separable from the unfinished CSP
architecture and are recommended for promotion to `main` together with their
tests:

| Accepted control | Application files | Regression evidence | Recommendation |
| --- | --- | --- | --- |
| Production-aware trusted hosts and Permissions Policy | `app/config.py`, `app/server_hooks.py` | `tests/unit/test_config.py`, `tests/integration/test_server_hooks.py` cover the exact production inventory, hostile hosts, localhost, response policy, and unchanged HTTPS/forwarded-protocol behavior | Promote |
| Enum/finite-number validation and stable caught-exception messages | `src/double_pendulum/validation/__init__.py`, `src/double_pendulum/validation/dash.py`, `src/double_pendulum/validation/inputs.py`, `app/callbacks/simulation.py` | `tests/unit/test_validation.py` and `tests/integration/test_simulation_interaction_shell.py` cover all configuration enums, every relevant numeric input category, callback rejection, safe stepper handling, stable browser messages, and server logging | Promote |
| Explicit new-tab relationship protection | `app/components/references.py` | `tests/unit/test_components.py` checks every generated reference link | Promote |

These controls are independently useful application hardening. None requires
CSP hashes, nonces, policy modes, callback-registration changes, Cloudflare
configuration, or another deferred architectural change. Trusted-host
validation is deployment-aware rather than generic: it is correct for the
verified `FORCE_HTTPS=true` production model and exact three-host inventory,
and must be reviewed whenever either fact changes.

Closeout verification on 2026-08-20 passed all 117 focused tests covering the
proposed promotion files in 6.07 seconds and the complete 227-test suite in
8.46 seconds. The earlier production-mode local import smoke also accepted the
apex and direct Railway hosts, rejected a hostile host, and emitted the exact
Permissions Policy. Live post-deployment verification remains outstanding and
is an operational follow-up, not a reason to couple Pass 1 to future CSP work.

`SECURITY_AUDIT.md` must remain only on `feat_CSP`; it is not recommended for
promotion or copying to `main`. At closeout review time the Pass 1 application,
test, and audit refinements are uncommitted changes on top of branch HEAD
`673b9dc`. The branch-only history since merge base `87f74d4` also contains the
audit commits `ebddeba` and `db7ec44`. Commit `673b9dc` is an unrelated sidebar
style change whose resulting file content already matches `main` commit
`1f4bc8d`; it is not part of Security Pass 1. A branch merge is therefore the
wrong promotion mechanism even though that style content currently converges.

Before promotion, create one commit containing only the twelve Pass 1
application and test files in the table above, then create a separate closeout
commit containing only `SECURITY_AUDIT.md`. Cherry-pick only the application
and test commit onto an up-to-date `main`. This preserves the branch-local
documentation boundary and avoids importing the branch's divergent audit and
style history.

The concrete future resume point is Pass 2 CSP scaffolding in `off` or
report-only mode. Before resuming, first re-verify the production host
inventory, `FORCE_HTTPS` deployment state, Railway build/start configuration,
and Cloudflare JavaScript Detections behavior. Then implement the already
proposed dedicated CSP builder/mode parser, callback-registration ordering,
validated Dash hashes, per-response nonce design, and exact policy tests. Pass
3 remains the production report-only observation period, and Pass 4 remains
enforcement only after that evidence is accepted.

Availability/origin controls, HTTPS/HSTS migration, dependency provenance,
Cloudflare changes, rate limiting, request-body limits, Railway ingress,
Canvas/result-state redesign, Gunicorn tuning, and dependency upgrades remain
intentionally deferred. They are not prerequisites for promoting Pass 1 and
must not be bundled into the selective promotion.

## Current deployed surface

The intended public application surface is small:

- public Dash navigation routes;
- `GET /_dash-layout` and `GET /_dash-dependencies`;
- `POST /_dash-update-component`;
- same-origin Dash component bundles and `/assets/` files;
- `GET /robots.txt`; and
- the standard inactive `GET /_reload-hash` endpoint.

There is no authentication, account, database, upload, email, payment, user
content, server-side session, application cookie, or privileged administration
surface in the repository. There is no Flask CORS extension, proxying endpoint,
arbitrary filesystem read, subprocess route, or server-side outbound fetch.

Markdown and TeX content is repository-owned. `dcc.Markdown` is not configured
with `dangerously_allow_html`. The Canvas JavaScript uses DOM APIs and
`textContent`; it does not use `eval`, `new Function`, `innerHTML`, fetch,
WebSockets, local storage, or session storage. External GitHub, book, and
reference URLs are navigational links, not runtime resource origins.

Dash serves every tracked file below `assets/`. This makes
`custom-header.html`, Markdown source files, licences, JavaScript, CSS, images,
and fonts publicly retrievable. None contained secrets, and most content is
already public through the UI. Moving non-runtime templates/content out of the
assets tree is optional hygiene, not a material security pass.

## Responsibility boundaries

| Control | Primary owner | Defence-in-depth / trade-off |
| --- | --- | --- |
| CSP source list, Dash hashes, CSP mode, policy regression tests | Dash/Flask application | The policy is release-coupled to generated application scripts. Do not add a second independent Cloudflare CSP: multiple policies intersect and can break Dash. Cloudflare must remain compatible with the nonce because it injects JavaScript Detections. |
| Browser HTTPS redirect | Railway currently; Cloudflare edge as the recommended custom-domain owner | Railway is confirmed to redirect both custom-domain and generated-host HTTP before Flask. Cloudflare **Always Use HTTPS** would duplicate the custom-domain outcome but make public-edge ownership explicit. The application hook is currently a fallback, not the observed production redirect owner. |
| HSTS | Cloudflare edge / browser-facing policy | Cloudflare can own HSTS for the custom domains. If the Railway hostname remains an intentionally supported browser ingress, Cloudflare cannot cover it and Railway or the application must separately own its host-specific HSTS after the architecture decision. |
| Origin TLS and certificate lifecycle | Railway | Cloudflare chooses validation mode; Railway controls what certificate the origin presents. Full (strict) requires evidence at this boundary, not the Cloudflare edge certificate. |
| Forwarded scheme and host trust | Railway contract plus Dash/Flask application | Live tests confirm Railway currently normalizes external protocol values. The app should depend only on that observed contract; incorrect broad `ProxyFix` remains worse than the existing narrow scheme check. |
| Valid hostnames | Dash/Flask application | Cloudflare host routing cannot protect the direct Railway ingress. The initial recommended production allowlist is the apex, `www`, and the generated Railway hostname; no health-check host/path is currently required. |
| WAF scanner rule | Cloudflare edge | Keep the supplied opportunistic-probe rule at the edge. Do not add Flask routes to duplicate it. The existing generic/plain-404 application handling can remain direct-origin defence in depth. |
| Numerical request validation and body-size limit | Dash/Flask application | Only the app knows valid fields and computational cost. A global cap must accommodate the measured multi-megabyte Canvas state round-trip or follow a callback-state refactor; Railway/Cloudflare limits are broader safeguards, not substitutes. |
| Callback rate limiting and bot controls | Cloudflare edge, conditional on ingress architecture | Rate limiting before Railway avoids consuming the worker on custom-domain traffic, but the public Railway hostname bypasses it. Either accept partial edge coverage, add a coordinated application/deployment control, or make Cloudflare the required ingress. |
| Gunicorn worker count, timeout, memory, and deploy flags | Railway/deployment | Changes require measurement on the actual Railway service size. More workers improve concurrency but multiply NumPy/SciPy/SymPy memory. |
| `nosniff`, referrer policy, framing policy, permissions policy | Dash/Flask application | These are stable application requirements and are easy to version and test. Cloudflare should not overwrite them unless it is deliberately the single owner. |
| Direct-origin policy | Railway architecture decision; application baseline regardless | Keeping the generated hostname provides a diagnostic/fallback ingress but means Cloudflare controls are enhancements, not universal controls. If Cloudflare must become the only ingress, first verify Railway can remove the generated domain without harming deployment operations; an overwritten origin-secret is a viable but outage-sensitive fallback. |

## Material findings

### F1. No CSP is deployed; Dash and Cloudflare both create inline-script requirements

**Status:** confirmed repository and production finding  
**Priority:** High implementation priority / Medium present risk  
**Enforcement layer:** application-owned browser policy, with Cloudflare nonce compatibility

**Current state**

There is no `Content-Security-Policy` or
`Content-Security-Policy-Report-Only` response header. All application runtime
resources are same-origin, but the HTML contains executable inline code.

**Evidence**

- `pendulum_app.py` registers two Python-string clientside callbacks.
- Dash emits those as two inline scripts plus
  `var renderer = new DashRenderer();`.
- `app.csp_hashes()` currently returns three SHA-256 sources covering those
  application blocks.
- `configure_server()` is currently called before callback registration. A CSP
  implementation must change this ordering before it snapshots Dash hashes.
- Production HTML contains an additional changing Cloudflare bootstrap that
  loads same-origin `/cdn-cgi/challenge-platform/scripts/jsd/main.js`.
  Cloudflare JavaScript Detections and Bot Fight Mode are confirmed enabled,
  so this is an intentional edge feature. Direct Railway responses bypass the
  feature and its injection.
- Cloudflare documents that JavaScript Detections will fail under
  `script-src 'self'` unless its injection receives an allowed nonce; it also
  documents that it propagates a nonce parsed from a CSP response header.
- A local candidate policy worked without `'unsafe-eval'` or script
  `'unsafe-inline'`.

**Actual risk**

The app has little untrusted-content surface, so lack of CSP is not by itself a
demonstrated exploit. It does remove an important browser boundary if a future
markup/script injection defect or compromised same-origin asset path appears.
An incorrect first policy is the more immediate operational risk: it could
leave the application at `Loading...`, stop callbacks, prevent MathJax, or
disable Cloudflare bot signals.

**Recommended mitigation**

1. Add a small CSP module and `off` / `report-only` / `enforce` deployment mode.
2. Register all callbacks before collecting `app.csp_hashes()` and configuring
   the server hook.
3. Validate and include Dash's three hashes in `script-src`.
4. Generate an unpredictable nonce per HTML response and include it in
   `script-src` so Cloudflare can attach it to JavaScript Detections. Verify the
   nonce is actually present on the injected production script before enforce.
5. Keep `/cdn-cgi/challenge-platform/` allowed through same-origin
   `script-src`; do not add a broad Cloudflare domain wildcard.
6. Start with a policy equivalent to:

   ```text
   default-src 'self';
   script-src 'self' <three Dash SHA-256 sources> 'nonce-<per-response-value>';
   script-src-attr 'none';
   style-src 'self' 'unsafe-inline';
   img-src 'self' data:;
   font-src 'self';
   connect-src 'self';
   object-src 'none';
   base-uri 'none';
   frame-ancestors 'self';
   form-action 'self';
   worker-src 'none';
   manifest-src 'none';
   media-src 'none'
   ```

   This is a target for implementation testing, not a policy applied by this
   audit.
7. Add response-header, hash-ordering, local-enforcement, route, MathJax, and
   Canvas regression tests. Make `off` an immediate CSP-only rollback.

Do not place the same policy independently in Flask and a Cloudflare Transform
Rule. CSP headers combine restrictively; they do not merge into a convenient
union.

### F2. Runtime-generated CSS blocks a strict style policy

**Status:** confirmed  
**Priority:** Medium for CSP planning; Low as a standalone risk  
**Enforcement layer:** browser-facing application policy

**Current state**

The app stylesheet is local, but Dash, DCC, React components, Markdown
highlighting, and MathJax create runtime `<style>` elements and style
attributes. Application layouts also deliberately use Dash `style={...}`
properties.

**Evidence**

The live Equations page contained 16 runtime style elements, including
`MJX-CHTML-styles`, and 352 elements with a style attribute. None carried a
nonce. The local candidate CSP worked only with an inline-style allowance.

**Actual risk**

`style-src 'unsafe-inline'` weakens style-injection protection and prevents the
first CSP from being maximally restrictive. It does not permit script execution
and is materially safer than permitting unsafe scripts. Attempting to remove it
now would break core framework rendering.

**Recommended mitigation**

Accept and document `style-src 'unsafe-inline'` in the initial report-only and
enforced policies, as the population-dynamics prototype does. Do not postpone
script, object, base, frame, font, image, or connection restrictions while
waiting for a complete CSS architecture change. Revisit `style-src-elem` and
`style-src-attr` only in a later measured compatibility pass.

### F3. Unauthenticated numerical callbacks expose the default worker model to availability abuse

**Status:** confirmed repository/deployment and local measurement finding; production callback rate-limit state remains unverified\
**Priority:** High\
**Enforcement layer:** application validation plus Cloudflare rate limiting and Railway capacity controls

**Current state**

Any client can post directly to the Dash callback endpoint and request a
simulation. Validation caps duration at 60 seconds and therefore caps the
current output request at 12,000 time samples. Parameter, mass, length,
gravity, angle, and angular-velocity bounds are also present. These are
important positive controls. Pass 1 additionally rejects unknown model,
formulation, and named integrator-policy strings before model construction and
requires finite, non-boolean values across the numerical input surface.

The repository-declared production command is only:

```text
gunicorn pendulum_app:server
```

If Railway uses that unmodified command, Gunicorn's effective defaults are one
sync worker, one thread, a 30-second timeout, and unlimited requests per
worker. Flask has no configured
`MAX_CONTENT_LENGTH`. The supplied Cloudflare custom rule blocks scanner paths;
it is not a callback rate limit. Bot Fight Mode and JavaScript Detections are
enabled, but both are bypassed through the public Railway hostname.

**Evidence**

- `build_simulation_run_result()` constructs either a Lagrangian or Hamiltonian
  model, runs SciPy integration, precomputes positions, validates a large
  payload, and serializes arrays in one request.
- SymPy, SciPy, NumPy, and model construction execute in the web worker.
- A normal browser simulation completed under test, confirming that the public
  callback is the production computation path.
- Crafted requests can send their own Dash state rather than being limited to
  values produced by the visible controls.
- Real callback-envelope measurements found approximately 2 KB simulation-run
  requests, 0.22-2.11 MB responses, and 0.058-2.25 seconds of local CPU/wall
  time depending on caches and path. CPU and wall time tracked closely.
- The 60-second valid envelope returned 12,000 samples. The largest response
  measured 2,113,053 bytes.
- A legitimate input-change callback then posted that Canvas state back to the
  server in a 2,112,330-byte request and returned 2,113,430 bytes. This is a
  framework/application state-flow cost, not a malicious oversized request.

**Actual risk**

A small number of repeated valid expensive requests can queue or time out users
under the repository-default one-worker configuration. Large JSON bodies can
consume parsing memory before field-level validation. This is an availability
risk, not an authentication or data-confidentiality risk. The measured local
cases did not approach the 30-second timeout, but they do not establish Railway
service capacity or concurrent behavior. A Cloudflare-only rate limit would
reduce custom-domain load while leaving the direct Railway path available for
bypass.

**Recommended mitigation**

1. Repeat the representative cold/warm measurements on the Railway service size
   or use Railway metrics during a controlled run before changing concurrency.
2. Do **not** add a global body cap in Pass 1 from the 2 KB run-request figure.
   First remove/bound the multi-megabyte Canvas store round-trip or measure its
   complete valid envelope and choose explicit headroom. Then add a tested cap
   with a generic `413`.
3. Explicitly allowlist model, system, and solver-policy enum values and reject
   non-finite numeric input before model construction. **Implemented in Pass 1;
   retain the regression coverage.**
4. Configure a Cloudflare rate-limit rule specifically for
   `POST /_dash-update-component`, with enough burst capacity for normal Dash
   use. Observe before blocking, do not invent a threshold from a single-user
   local test, and document that coverage is partial while direct Railway
   access remains public.
5. Evaluate Railway/Gunicorn concurrency only with memory measurements. An
   explicit small worker count or `WEB_CONCURRENCY` may help, but importing the
   numerical stack per worker is expensive.
6. Consider `max_requests` plus jitter only if deployment evidence shows
   long-lived worker memory growth.

### F4. The public Railway ingress bypasses Cloudflare controls by design

**Status:** confirmed production architecture finding\
**Priority:** Medium; High for any control incorrectly treated as universal\
**Enforcement layer:** Railway architecture decision plus application baseline

**Current state**

`https://web-production-65a59.up.railway.app` directly serves the application.
The known host inventory is the apex, `www`, and this generated hostname. No
Railway health-check path is configured. There is no origin-authentication
header or application rule requiring traffic to have passed through
Cloudflare.

**Evidence**

- Direct Railway HTTPS returned `200` with `server: railway-hikari` and the
  application-owned response headers, without Cloudflare response headers.
- Direct Railway HTTP returned Railway's pre-Flask `301` to the same hostname
  over HTTPS.
- Cloudflare Bot Fight Mode, JavaScript Detections, the scanner rule, any future
  Cloudflare rate limit, Cloudflare Always Use HTTPS, and Cloudflare HSTS exist
  only on the proxied custom-domain path.

**Actual risk**

The hostname permits deliberate bypass of every Cloudflare-only protection.
Today that concretely bypasses the scanner rule, Bot Fight Mode, and JavaScript
Detections. It would also bypass a future callback rate limit, so that rate
limit cannot be described as complete availability protection while this
ingress remains public. It does not bypass Flask input validation, generic 404
handling, application security headers, or a future application-owned CSP.

Public origin access is not automatically a vulnerability. It can provide a
useful Railway diagnostic/fallback URL and a way to distinguish origin from
Cloudflare incidents. The trade-off is architectural: either it is a supported
second ingress whose security baseline must be application/deployment-owned,
or Cloudflare becomes the required ingress and the diagnostic path is given up
or replaced by a controlled mechanism.

**Recommended target decision**

1. For Pass 1, keep all controls that protect confidentiality/integrity or
   constrain application inputs at Flask/Dash regardless of Cloudflare. Include
   all three current production hosts in `TRUSTED_HOSTS` if direct Railway
   access is retained. No health-check exception is presently needed.
2. Before rate-limit enforcement, choose and document one target architecture:
   **dual public ingress**, accepting that Cloudflare controls cover only the
   custom domains; or **Cloudflare-required ingress**, making the edge controls
   universal.
3. If Cloudflare-required ingress is chosen, first verify in Railway whether the
   generated domain can be removed while custom domains, deploy readiness, and
   diagnostics continue to work. Do not block it merely because it exists.
4. If Railway cannot make the origin private and universal edge enforcement is
   required, the population-dynamics overwritten-secret-header pattern is a
   viable fallback. Stage the Cloudflare overwrite before application
   enforcement, compare in constant time, cover both custom hosts, and retain a
   tested rollback. This deliberately makes the direct Railway URL unavailable.

Authenticated Origin Pulls is not practical unless Railway adds supported
managed-origin client-certificate validation.

### F5. Railway normalizes external scheme today; production host validation is now enforced

**Status:** Pass 1 mitigation implemented; production deployment verification pending\
**Priority:** Medium\
**Enforcement layer:** Dash/Flask application informed by Railway's proxy contract

**Current state**

When `FORCE_HTTPS` is enabled, the application reads the first comma-separated
`X-Forwarded-Proto` value directly. It treats `https` as authoritative and
otherwise constructs a redirect from `request.url`. No `ProxyFix` is installed.

Pass 1 configures Flask `TRUSTED_HOSTS` for the three verified production hosts
when `FORCE_HTTPS=true`. This rejects unknown hosts before they can influence
the fallback redirect. With `FORCE_HTTPS=false`, trusted-host enforcement is
disabled so localhost and `127.0.0.1` development remain available.

Gunicorn's default `forwarded_allow_ips` trusts only loopback addresses, while
the application bypasses that Gunicorn decision by reading the raw header.
Production has `FORCE_HTTPS=true`; it is the only configured Railway variable.

**Evidence**

- `app/server_hooks.py:force_https_redirect()` reads
  `X-Forwarded-Proto` and uses `request.url`.
- tests prove that a client-supplied `X-Forwarded-Proto: https` suppresses the
  application redirect when calling Flask directly.
- tests accept the apex, `www`, and generated Railway hostname in production
  mode and return `400` for hostile HTTPS and HTTP hosts;
- tests accept localhost and `127.0.0.1` when production mode is off;
- External HTTP is redirected at Railway before Flask, even when the client
  supplies `X-Forwarded-Proto: https`.
- External HTTPS returned `200`, rather than a same-URL redirect, when clients
  supplied first-value `http` and conflicting comma-separated protocol values.
  This proves the hostile external value does not survive to the hook in a form
  that controls its decision. The exact internal header representation was not
  captured, so this conclusion is deliberately limited to observed behavior.

**Actual risk**

No external scheme-spoof or redirect-loop defect was reproduced at the current
Railway boundary, and the known-host gap is mitigated in code. The remaining
risk is configuration drift: the application deliberately treats
`FORCE_HTTPS=true` as its production-mode signal, and the Railway-generated
hostname is release configuration. A changed production flag or hostname can
cause either missing enforcement or rejected legitimate traffic.

**Recommended mitigation**

1. Deploy Pass 1 independently and verify the apex, `www`, and direct Railway
   host. Confirm the generated hostname before every host-inventory change. No
   health-check exception is currently evidenced.
2. Preserve the regression tests for first-value parsing and record
   Railway normalization as a deployment assumption. Recheck it if Railway,
   Gunicorn, or ingress topology changes.
3. Do not introduce `ProxyFix` in Pass 1. No current defect requires it, and
   the exact trusted hop count for every forwarded header has not been
   established.
4. Retain the Flask hook only as a fallback. If it is later rewritten, construct
   redirects from validated hosts and a documented scheme signal.

### F6. HTTPS redirect behavior exists, but HSTS ownership is incomplete

**Status:** confirmed production finding  
**Priority:** Medium  
**Enforcement layer:** Cloudflare edge and browser-facing transport policy

**Current state**

Cloudflare settings supplied for this audit are:

- SSL/TLS: Full (automatic)
- Always Use HTTPS: off
- HSTS: off

Nevertheless, public HTTP requests to both apex and `www` returned a `301` to
HTTPS. Those redirect responses lacked the three Flask-added security headers
and included a Railway marker. Direct HTTP to the generated Railway hostname
returned the same form of response, and spoofed protocol headers did not change
it. The observed redirect owner is therefore Railway's public edge, before the
current Flask hooks.

**Actual risk**

Users are redirected today, but enforcement ownership is implicit and there is
no browser memory of the HTTPS requirement. The first HTTP request remains
subject to downgrade until HSTS has been learned. Enabling HSTS prematurely can
make hostnames inaccessible if their HTTPS support later fails. Turning on
Cloudflare Always Use HTTPS would duplicate the existing redirect outcome for
the custom domains; the value is explicit edge ownership and earlier handling,
not closure of a current redirect gap. It would not control the Railway
hostname.

**Recommended target and migration order**

1. Treat apex, `www`, and the generated Railway hostname as the current browser
   host inventory. Decide whether the Railway hostname remains a supported
   public ingress before assigning HSTS ownership.
2. Enable Cloudflare **Always Use HTTPS** so the custom-domain edge is the
   explicit enforcement point. Re-test path and query preservation.
3. Keep the Flask redirect as a documented fallback; Railway currently handles
   all observed public HTTP paths before it.
4. After a stable observation period, enable Cloudflare HSTS with a short
   `max-age`, without `includeSubDomains` and without preload.
5. If the Railway hostname is intentionally user-facing, separately determine
   whether Railway or an application header should supply HSTS there. A
   Cloudflare zone setting cannot cover another registrable domain.
6. Increase `max-age` gradually. Add `includeSubDomains` only after every
   subdomain is inventoried and HTTPS-only. Treat preload as a separate,
   difficult-to-reverse decision, not part of the initial hardening.

### F7. Full (strict) is not currently an appropriate unqualified Railway recommendation

**Status:** recommendation requiring deployment/provider verification  
**Priority:** Medium transport hardening, but do not change now  
**Enforcement layer:** Cloudflare origin mode constrained by Railway certificate behavior

**Current state**

Full encrypts Cloudflare-to-Railway traffic but does not require Cloudflare to
validate the origin certificate. Full (strict) would add origin certificate
validation and would normally be preferable.

**Evidence**

Cloudflare requires an unexpired, trusted origin certificate whose CN/SAN
matches the requested or target hostname. Railway automatically issues custom
domain certificates where it can, but its current Cloudflare-specific guidance
states that orange-cloud proxied domains may receive the default Railway
`*.up.railway.app` certificate and explicitly says to use Full, not Full
(strict). A valid certificate observed in a browser proves only the
visitor-to-Cloudflare connection, not the certificate Cloudflare sees from
Railway.

**Actual risk**

Remaining on Full leaves the Cloudflare-to-origin connection encrypted but not
cryptographically authenticated by Cloudflare. Switching to Full (strict)
without origin evidence can produce Cloudflare `526` failures and take the
public site offline.

**Recommended mitigation**

Keep Full as the supported target state for the current architecture. Revisit
Full (strict) only when all of the following are true:

- Railway shows the custom domain verified and the relevant certificate issued;
- the actual certificate/SNI behavior on the Cloudflare-to-Railway connection
  is verified, not inferred from the edge certificate;
- Railway documentation or support confirms Full (strict) for this exact
  proxied custom-domain arrangement; and
- there is a hostname-scoped test and immediate rollback plan for `526`.

Do not install a Cloudflare Origin CA certificate: Railway's managed custom
domain service does not support customer-supplied external certificates.

### F8. Browser security headers are application-owned; Pass 1 adds Permissions Policy

**Status:** Pass 1 mitigation implemented; production deployment verification pending
**Priority:** Low outside the CSP/HSTS findings  
**Enforcement layer:** Dash/Flask application

**Current state and evidence**

`app/server_hooks.py` sets:

- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `X-Frame-Options: SAMEORIGIN`
- `Permissions-Policy: camera=(), microphone=(), geolocation=()`

The exact same values appeared on HTML, static asset, Dash JSON, and reload
responses. They also appeared through the direct Railway hostname without
Cloudflare, so their origin is confirmed as Flask rather than Cloudflare or
Railway. Pass 1 adds and tests `Permissions-Policy` in the same Flask response
hook.

**Actual risk**

The present values are suitable, and unused camera, microphone, and geolocation
capabilities are now disabled. Framing is already limited; CSP
`frame-ancestors 'self'` should become the modern paired control in a later
pass.

**Recommended mitigation**

Retain the tested application-owned policy:

```text
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

Keep `X-Frame-Options: SAMEORIGIN` when CSP adds matching
`frame-ancestors 'self'`. Do not add obsolete `X-XSS-Protection`, HPKP, COEP, or
cross-origin isolation headers without an application requirement.

### F9. MathJax is fully local at runtime; provenance and maintenance remain manual

**Status:** confirmed positive control with a low-priority supply-chain gap  
**Priority:** Low  
**Enforcement layer:** repository/application supply chain

**Current state**

The app vendors MathJax 3.2.0 as one combined JavaScript entry point, 23
CommonHTML fonts, and the Apache-2.0 licence. The index uses a prefix-aware
same-origin URL. The production runtime and representative font returned
successfully. Browser observation and server logs showed MathJax loading only
local fonts. The only URLs embedded in the bundle were MathML and MathJax
project identifiers, not external runtime dependencies.

**Actual risk**

The CDN supply-chain and availability dependency has been removed. The
remaining gap is provenance: there is no npm lockfile, upstream tarball
integrity value, or checked manifest tying the copied subset to the official
`mathjax@3.2.0` package. Version 3.2.0 is also behind the final 3.2.x release
used by the population-dynamics reference. OSV reported no known advisory for
3.2.0, so this is maintenance debt rather than a confirmed vulnerability.

**Recommended mitigation**

- Record the official npm package version and `dist.integrity` or an equivalent
  tarball SHA-256 in temporary vendor documentation/tests.
- Add deterministic hashes for the copied entry point and font inventory, or a
  documented script that verifies an unpacked official tarball.
- Consider a separate compatibility-tested update to MathJax 3.2.2. Do not mix
  a major MathJax 4 migration into the first CSP pass.
- Preserve the local-only network assertion in integration tests and a browser
  network check on math-heavy routes.

### F10. Python dependency locking is good; advisory checks are manual

**Status:** confirmed repository lock; production install mode still requires build-log verification\
**Priority:** Low\
**Enforcement layer:** repository and deployment supply chain

**Current state and evidence**

`uv.lock` resolves 48 packages, with 47 registry packages and no VCS or direct
URL dependency. Runtime versions observed in production for Dash and Plotly
match the lock. Registry artifacts carry lockfile hashes. A current advisory
scan reported no application-package vulnerability.

The repository declares Python 3.12 and `web: gunicorn pendulum_app:server` and
contains no alternative Railway, Docker, Nixpacks, active root requirements, or
CI deploy configuration. The old freeze under `legacy/` is not an active build
input. Railway's current default builder documentation says Railpack
detects Python projects; Railpack documents uv selection from the pair of
`pyproject.toml` and `uv.lock` and automatic use of the Procfile `web` command.
This is the expected build/start path. However, Railway service-level install,
build, and start overrides are not stored here. No production build log or
settings export was available to prove the selected builder, exact uv flags,
dev-group exclusion, or absence of a start-command override.

The local environment's `pip==26.1.1` advisory is not represented in
`uv.lock`; it is tooling/build-environment hygiene, not evidence of a vulnerable
import in the deployed app.

**Actual risk**

The committed application environment is reproducible when installed from the
lock, but this audit cannot yet prove every production artifact came from that
path. Matching key live versions is good corroboration, not full supply-chain
attestation. A new advisory can also remain unnoticed between manual audits.
Broad direct requirements in
`pyproject.toml` also make an intentional lock refresh capable of selecting
new major versions, even though ordinary locked installs remain deterministic.

**Recommended mitigation**

- Inspect the next Railway build log and Build/Deploy settings for the builder,
  source commit, exact dependency command, locked/frozen behavior, development
  group handling, and start-command override. Record the result without
  changing the dependency strategy in this branch.
- Add a repeatable runtime export plus `pip-audit` check to the development or
  CI workflow when such automation is introduced.
- Upgrade the local environment's pip tooling to a fixed version without adding
  `pip` as an application dependency.
- Keep dependency upgrades separate from CSP enforcement unless a security fix
  requires coupling them.

### F11. Production debug mode is not exposed; handled exception text is now redacted

**Status:** Pass 1 information-disclosure mitigation implemented
**Priority:** Low  
**Enforcement layer:** Dash/Flask application and Railway deployment variables

**Current state**

`DASH_DEBUG` defaults false and is used only inside the
`if __name__ == '__main__'` local runner. Gunicorn imports
`pendulum_app:server`, so that block cannot run in production. Live Dash config
showed development UI and property checks disabled, and hot reload inactive.
Railway production variables contain only `FORCE_HTTPS=true`; no debug or
Flask environment override is configured.

Pass 1 keeps the existing handled failure states but replaces raw exception
strings with stable solver-setup and output-preparation messages. The original
exceptions are logged server-side with run ID, model, and formulation context.
Intentional numerical solver metadata remains visible as educational
diagnostics; it is not populated from a caught exception.

**Actual risk**

There is no exposed Werkzeug/Dash debugger, and the handled callback exception
paths no longer copy exception text into browser state. Request correlation IDs
are not yet added to these application log messages, so cross-system incident
tracing still depends on Railway/platform logging context.

**Recommended mitigation**

Preserve the stable public messages and server-side exception logging. A
request-correlation helper may be added with later observability work, but it
is not required to prevent the disclosure. Verify the same variable state
after material deployment configuration changes; changing `DASH_DEBUG`
currently does not affect Gunicorn import, but deployment variables should
still reflect intent.

### F12. External-link opener protection is explicit and consistent

**Status:** resolved in Pass 1
**Priority:** Low / opportunistic  
**Enforcement layer:** application markup

**Current state and evidence**

Home and footer links opened with `target="_blank"` also set
`rel="noopener noreferrer"`. Pass 1 applies the same explicit value to reference
links created by `app/components/references.py`; a component regression test
checks every generated reference link.

**Actual risk**

Modern browsers implicitly apply `noopener` to `_blank`, so the original gap
was low impact. Explicit consistency now protects older or embedded clients and
makes intent reviewable.

**Recommended mitigation**

Retain explicit `rel="noopener noreferrer"` for every new-tab link. This is not
a CSP blocker.

## Existing Cloudflare scanner rule

The supplied rule is appropriately treated as edge-level opportunistic-probe
filtering. No Flask route or new application rule should be added merely to
mirror it.

The existing application `before_request` logic already returns minimal 404s
for PHP, WordPress, repository metadata, environment files, package manifests,
API-like paths, and dotted unknown paths. This remains useful for direct-origin
traffic and for correct Dash 404 behavior, but it must not be described as a
replacement for the Cloudflare rule. Expanding this duplicate list has little
security value.

## Pass 0 conclusion and remaining external verification

Security Pass 0 now provides a concrete ingress and application model. The
Railway variable/debug state, host inventory, absence of a health check, direct
origin reachability, current redirect owner, externally observable forwarded
scheme behavior, Cloudflare bot/JavaScript settings, application callback
sizes, and local callback cost are confirmed findings.

The following items remain explicitly unconfirmed because repository and HTTP
evidence cannot answer them:

- the Railway service's selected builder, build/start overrides, exact uv
  install flags, dev-group handling, and deployed lock/source identity;
- Railway instance CPU/memory, replica count, cold-start behavior, concurrent
  callback performance, and memory use;
- whether any separate Cloudflare rule already rate-limits the Dash callback
  path beyond the supplied scanner rule; and
- the Cloudflare-to-Railway certificate/SNI behavior needed to reconsider Full
  (strict).

The first item should be checked in Railway Build/Deploy settings and the next
build log. The second belongs to the later availability pass. The third belongs
to Cloudflare rate-limit discovery before proposing a threshold. The fourth is
not a blocker: Full remains the provider-supported target for the current
architecture. None of these uncertainties justifies delaying the small,
application-only Pass 1 guards.

## Recommended target state

### Application

- CSP module with explicit modes, validated Dash hashes, and tests.
- CSP configured after all clientside callbacks are registered.
- Per-response CSP nonce compatible with Cloudflare JavaScript Detections.
- Initial enforced policy has no unsafe script/eval and retains only the
  documented inline-style allowance.
- Production-aware `TRUSTED_HOSTS` covers the apex, `www`, and the intentionally
  retained Railway hostname; local mode does not enforce production hosts.
- Narrow application-owned `Permissions-Policy`.
- Finite/enum validation and stable public solver exception messages.
- A request-body cap only after the legitimate Canvas state round-trip is
  removed or completely bounded; no guessed Pass 1 cap.
- Existing low-risk headers retained.

### Railway/deployment

- Gunicorn remains the production server; debug variables remain off.
- Worker/concurrency settings are explicit only after memory and request-cost
  measurements.
- Locked dependency installation is verified from build logs.
- The three current public hosts and absence of a health check are documented.
- The generated-host ingress is retained or removed only through an explicit
  architecture decision, not an automatic hardening reaction.
- Full remains the supported Cloudflare-to-Railway TLS mode unless Railway
  confirms a strictly validated alternative.

### Cloudflare

- Existing scanner rule retained at the edge.
- JavaScript Detections retained and verified with the application nonce.
- Callback rate limiting observed and then enforced at the edge only after its
  partial coverage or Cloudflare-required ingress is explicit.
- **Always Use HTTPS** becomes the explicit public redirect owner.
- HSTS is introduced with a short max-age, then increased; no initial
  `includeSubDomains` or preload.
- Optional origin-secret injection is considered only if the Railway origin
  cannot be made private and edge-bypass risk warrants it.
- No independent duplicate CSP unless application ownership is deliberately
  transferred as a whole.

### Browser-facing policy

- CSP restricts scripts, connections, fonts, images, objects, frames, forms,
  workers, manifests, and media to the minimum observed set.
- Same-origin framing remains allowed; cross-origin framing remains blocked.
- Referrer and MIME-sniffing policies remain unchanged.
- Unused powerful browser features are disabled.
- HSTS is delivered only after the HTTPS migration checks and with explicit
  ownership for any intentionally public Railway hostname.

## Proposed sequence of small implementation passes

### Pass 0: deployment fact verification — completed for planning

- Confirmed `FORCE_HTTPS=true` as the only Railway variable and no explicit
  debug configuration.
- Confirmed Railway's pre-Flask public edge as the current HTTP redirect owner
  and observed protocol-header normalization with no redirect loop.
- Confirmed the three-host inventory, no Railway health check, and direct
  Railway reachability.
- Confirmed Cloudflare Bot Fight Mode and JavaScript Detections are enabled.
- Measured representative callback request/response sizes and local CPU/wall
  cost, including the large legitimate Canvas-state POST.
- Confirmed repository deployment intent and recorded the remaining production
  build-log uncertainty rather than inferring it away.

No behavior change.

### Pass 1: low-risk application guards — implemented and locally verified

- Added production-mode `TRUSTED_HOSTS` for the exact three-host inventory while
  leaving local mode compatible with localhost and `127.0.0.1`.
- Added `Permissions-Policy`.
- Added explicit enum and finite-number validation across the simulation input
  surface.
- Added `rel="noopener noreferrer"` to generated reference links.
- Replaced raw caught-exception strings with stable browser messages and
  server-side logging.
- Added HTTPS/proxy, host, header, validation, exception, and link regression
  tests without adding `ProxyFix` or changing redirect behavior.
- Deliberately did not add a request-body limit; the measured valid Dash state
  flow remains multi-megabyte and needs a separate design decision.

The full local suite passed (227 tests). Deploy and verify this pass across all
three production hosts before beginning Pass 2.

### Pass 2: CSP scaffolding, initially off or report-only — paused; resume here

- Add a dedicated policy builder and mode parser.
- Move server-hook configuration after all callback registration.
- Capture and validate `app.csp_hashes()`.
- Add the per-response nonce design.
- Add unit/integration tests for exact directives and modes.
- Keep the inline-style limitation explicit.

Do not enforce in production in this pass.

### Pass 3: production CSP report-only observation — paused after Pass 2

- Deploy `Content-Security-Policy-Report-Only`.
- Verify Cloudflare adds the advertised nonce to its injected bootstrap.
- Exercise all public routes, dynamic navigation, MathJax, Canvas playback,
  invalid inputs, and callback requests.
- Inspect console/report data for unexpected origins, eval, workers, images,
  fonts, connections, and style behavior.
- Keep a tested `off` rollback.

### Pass 4: CSP enforcement — paused after Pass 3 evidence

- Enforce the observed policy with no unsafe script/eval.
- Retain `style-src 'unsafe-inline'` as the only unsafe source.
- Re-run browser and server tests through Cloudflare.
- Optionally move the two clientside callback functions into a namespaced asset
  later; this reduces release-coupled hashes but is not required for first
  enforcement because Dash's renderer bootstrap still needs handling.

### Pass 5: availability and origin controls

- Refactor or explicitly bound the Canvas payload round-trip in the input-change
  callback, then measure the full legitimate request envelope and introduce a
  tested application body cap with headroom.
- Repeat callback measurements against Railway capacity and use observation to
  design, rather than invent, a callback rate threshold.
- Decide whether the supported target is dual public ingress or
  Cloudflare-required ingress.
- Add an observed-then-enforced Cloudflare callback rate limit with its ingress
  coverage stated accurately.
- If Cloudflare-required ingress is chosen, verify whether the generated
  Railway hostname can be removed without operational loss.
- If necessary, stage a Cloudflare-overwritten origin secret with an
  application rollback.
- Tune Gunicorn only from Railway memory and concurrency evidence.

These controls should not be bundled into the CSP deployment.

### Pass 6: HTTPS and HSTS edge migration

- Keep Cloudflare/Railway Full while provider guidance requires it.
- Enable **Always Use HTTPS** and verify both hostnames, paths, and queries.
- Introduce short HSTS without subdomains/preload, observe, then increase.
- If direct Railway remains a supported browser ingress, assign and test its
  separate HSTS owner; Cloudflare cannot cover that hostname.
- Reassess Full (strict) only if the Railway origin certificate/SNI path becomes
  explicitly supported and verified.

### Pass 7: supply-chain maintenance

- Record MathJax upstream integrity/provenance.
- Consider the separate 3.2.2 maintenance update.
- Make the application dependency advisory audit repeatable.
- Verify the deployment uses the committed lockfile without opportunistic
  re-resolution.

## External references used

- Dash clientside callbacks and asset-based functions:
  <https://dash.plotly.com/clientside-callbacks>
- Dash external resources and index template behavior:
  <https://dash.plotly.com/external-resources>
- Flask proxy guidance and the warning to trust the exact proxy count:
  <https://flask.palletsprojects.com/en/stable/deploying/proxy_fix/>
- Cloudflare Full (strict) origin-certificate requirements:
  <https://developers.cloudflare.com/ssl/origin-configuration/ssl-modes/full-strict/>
- Railway custom domains, certificates, and Cloudflare Full guidance:
  <https://docs.railway.com/networking/domains/working-with-domains>
- Railway Railpack build behavior and service-level configuration overrides:
  <https://docs.railway.com/builds/railpack>
- Railway build configuration and Procfile detection:
  <https://docs.railway.com/builds/build-configuration>
- Railpack Procfile process selection and override order:
  <https://railpack.com/config/procfile/>
- Railpack Python detection, Python-version precedence, and uv lockfile path:
  <https://github.com/railwayapp/railpack/blob/main/docs/src/content/docs/languages/python.md>
- Railway start-command detection and override behavior:
  <https://docs.railway.com/deployments/start-command>
- Cloudflare JavaScript Detections and CSP nonce propagation:
  <https://developers.cloudflare.com/cloudflare-challenges/challenge-types/javascript-detections/>
- Cloudflare CSP product interactions:
  <https://developers.cloudflare.com/fundamentals/reference/policies-compliances/content-security-policies/>
- Cloudflare HSTS requirements and rollout cautions:
  <https://developers.cloudflare.com/ssl/edge-certificates/additional-options/http-strict-transport-security/>
