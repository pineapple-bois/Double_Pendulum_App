# Deployed Application Security Audit

Date: 2026-08-18  
Branch: `feat_CSP`  
Status: audit and hardening plan only; no application or infrastructure controls were changed

## Executive summary

No critical compromise, secret exposure, production debugger, external runtime
CDN dependency, or known vulnerable application dependency was identified.

The most important findings are:

1. The public numerical callback is an unauthenticated CPU and memory workload
   behind Gunicorn's default single synchronous worker. Input bounds are useful,
   but there is no evidenced request-rate control or application request-body
   cap. Availability is the clearest current security risk.
2. A restrictive CSP is feasible, but it cannot be added as a simple static
   `script-src 'self'` header. Dash emits three executable inline scripts and
   the Cloudflare production path injects a fourth, changing inline JavaScript
   Detections bootstrap. Dash hashes can cover the application scripts;
   Cloudflare's documented nonce propagation should cover the edge injection.
   Runtime Dash and MathJax CSS still requires an inline-style allowance.
3. The application manually trusts `X-Forwarded-Proto` when `FORCE_HTTPS` is
   enabled and does not restrict trusted `Host` values. The exact Railway and
   Cloudflare forwarding contract must be verified before proxy middleware or
   redirect hardening is changed.
4. Public HTTP already redirects to HTTPS even though Cloudflare's **Always Use
   HTTPS** setting is off, but the redirect is not produced by the Flask hook.
   HSTS is absent. Cloudflare should ultimately own browser-to-edge HTTPS
   enforcement and HSTS.
5. **Do not move the current Railway/Cloudflare architecture to Full (strict)
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
  a changing inline bootstrap; and
- TLS 1.2 and TLS 1.3 handshakes to the Cloudflare edge succeeded. The minimum
  accepted edge TLS version was not established by this audit.

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
| Browser HTTPS redirect | Cloudflare edge | Railway currently appears to redirect before Flask. Cloudflare **Always Use HTTPS** should become the explicit public owner after verification. Keep an application redirect only as a documented fallback for direct-origin traffic. |
| HSTS | Cloudflare edge / browser-facing policy | The edge terminates public TLS and can guarantee the header on HTTPS responses. Do not emit it unconditionally from Flask until proxy and hostname behavior is proven. |
| Origin TLS and certificate lifecycle | Railway | Cloudflare chooses validation mode; Railway controls what certificate the origin presents. Full (strict) requires evidence at this boundary, not the Cloudflare edge certificate. |
| Forwarded scheme and host trust | Railway contract plus Dash/Flask application | The platform must overwrite forwarding headers; the app must trust only the values and hop count actually supplied. Incorrect `ProxyFix` is worse than a narrow verified implementation. |
| Valid hostnames | Dash/Flask application | Cloudflare host routing helps at the public edge, but `TRUSTED_HOSTS` also protects direct Railway access and URL construction. Keep health-check and Railway host requirements explicit. |
| WAF scanner rule | Cloudflare edge | Keep the supplied opportunistic-probe rule at the edge. Do not add Flask routes to duplicate it. The existing generic/plain-404 application handling can remain direct-origin defence in depth. |
| Numerical request validation and body-size limit | Dash/Flask application | Only the app knows valid fields and computational cost. Railway/Cloudflare body limits are broader safeguards, not substitutes. |
| Callback rate limiting and bot controls | Cloudflare edge | Rate limiting before Railway avoids consuming the single application worker. Application rate limiting would add state/coordination and is not the first choice here. |
| Gunicorn worker count, timeout, memory, and deploy flags | Railway/deployment | Changes require measurement on the actual Railway service size. More workers improve concurrency but multiply NumPy/SciPy/SymPy memory. |
| `nosniff`, referrer policy, framing policy, permissions policy | Dash/Flask application | These are stable application requirements and are easy to version and test. Cloudflare should not overwrite them unless it is deliberately the single owner. |
| Direct-origin restriction | Railway if supported; otherwise Cloudflare plus application | Prefer disabling an unnecessary Railway public domain. If not possible, a Cloudflare-overwritten secret header with constant-time application validation is a viable but outage-sensitive fallback. |

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

### F3. Unauthenticated numerical callbacks expose the single worker to availability abuse

**Status:** confirmed repository/deployment finding; production rate-limit state requires verification  
**Priority:** High  
**Enforcement layer:** application validation plus Cloudflare rate limiting and Railway capacity controls

**Current state**

Any client can post directly to the Dash callback endpoint and request a
simulation. Validation caps duration at 60 seconds and therefore caps the
current output request at 12,000 time samples. Parameter, mass, length,
gravity, angle, and angular-velocity bounds are also present. These are
important positive controls.

The production command is only:

```text
gunicorn pendulum_app:server
```

Gunicorn's effective defaults are one sync worker, one thread, a 30-second
timeout, and unlimited requests per worker. Flask has no configured
`MAX_CONTENT_LENGTH`. The supplied Cloudflare custom rule blocks scanner paths;
it is not a callback rate limit.

**Evidence**

- `build_simulation_run_result()` constructs either a Lagrangian or Hamiltonian
  model, runs SciPy integration, precomputes positions, validates a large
  payload, and serializes arrays in one request.
- SymPy, SciPy, NumPy, and model construction execute in the web worker.
- A normal browser simulation completed under test, confirming that the public
  callback is the production computation path.
- Crafted requests can send their own Dash state rather than being limited to
  values produced by the visible controls.

**Actual risk**

A small number of repeated valid expensive requests can queue or time out all
users on the only worker. Large JSON bodies can consume parsing memory before
field-level validation. This is an availability risk, not an authentication or
data-confidentiality risk.

**Recommended mitigation**

1. Measure representative simple/compound and Lagrangian/Hamiltonian cold and
   warm requests on the Railway service size.
2. Add a conservative application request-body cap after measuring the largest
   legitimate Dash request. Return a generic `413`.
3. Explicitly allowlist model, system, and solver-policy enum values and reject
   non-finite numeric input before model construction. The current validation
   allows `NaN` angle values to reach solver setup.
4. Configure a Cloudflare rate-limit rule specifically for
   `POST /_dash-update-component`, with enough burst capacity for normal Dash
   use. Observe before blocking and do not apply the scanner-path rule as a
   substitute.
5. Evaluate Railway/Gunicorn concurrency only with memory measurements. An
   explicit small worker count or `WEB_CONCURRENCY` may help, but importing the
   numerical stack per worker is expensive.
6. Consider `max_requests` plus jitter only if deployment evidence shows
   long-lived worker memory growth.

### F4. The direct Railway origin may bypass Cloudflare controls

**Status:** deployment verification required  
**Priority:** Medium, rising to High if the Railway-generated hostname is public and rate limiting is relied on  
**Enforcement layer:** Railway first; otherwise Cloudflare request transform plus application validation

**Current state**

The repository and public responses prove a Railway deployment, but the
Railway-provided hostname and whether it remains publicly reachable are not in
tracked configuration. Cloudflare WAF, JavaScript Detections, future rate
limits, HTTPS redirect, and future HSTS protect only traffic that traverses
Cloudflare.

**Evidence**

Production responses contain Railway request/edge headers behind Cloudflare.
There is no application origin-authentication header and no repository evidence
that a direct Railway hostname is disabled.

**Actual risk**

If the Railway hostname is discoverable and reachable, an attacker can bypass
the supplied Cloudflare scanner rule and any future edge-only callback rate
limit. The application still applies input validation and its generic 404
handling, so this is not a bypass of all controls.

**Recommended mitigation**

1. Inventory Railway public domains and test them without changing DNS.
2. Disable an unnecessary Railway-generated public hostname if Railway supports
   doing so while retaining the custom domain.
3. If it cannot be disabled, consider the population-dynamics origin-secret
   pattern: Cloudflare must **overwrite** a private request header, and the
   application must compare it in constant time before serving content.
4. Stage the Cloudflare rule before enabling application enforcement, include
   both public hostnames, account for health checks, provide a rollback, and
   never commit the secret.

Authenticated Origin Pulls is not a practical recommendation unless Railway
provides a supported way to install/validate Cloudflare client certificates at
the managed origin.

### F5. Forwarded-scheme trust is narrow but unverified, and host validation is absent

**Status:** confirmed application finding; Railway header behavior requires production verification  
**Priority:** Medium  
**Enforcement layer:** Dash/Flask application informed by Railway's proxy contract

**Current state**

When `FORCE_HTTPS` is enabled, the application reads the first comma-separated
`X-Forwarded-Proto` value directly. It treats `https` as authoritative and
otherwise constructs a redirect from `request.url`. No `ProxyFix` is installed,
and Flask `TRUSTED_HOSTS` is unset. A local request with
`Host: hostile.example` returned `200`.

Gunicorn's default `forwarded_allow_ips` trusts only loopback addresses, while
the application bypasses that Gunicorn decision by reading the raw header.

**Evidence**

- `app/server_hooks.py:force_https_redirect()` reads
  `X-Forwarded-Proto` and uses `request.url`.
- tests prove that a client-supplied `X-Forwarded-Proto: https` suppresses the
  application redirect.
- `server.config["TRUSTED_HOSTS"]` is `None`.
- Repository default `FORCE_HTTPS` is false. The production environment value
  is not visible from the repository.

**Actual risk**

If Railway does not overwrite forwarding headers, a direct client can spoof the
scheme and bypass the application fallback redirect. If a hostile `Host` reaches
the app while that redirect runs, it can influence `Location`. The Cloudflare
zone and Railway host routing reduce public exploitability, but they do not
justify trusting an unverified header path.

**Recommended mitigation**

1. Verify whether Railway overwrites or appends `X-Forwarded-Proto`, what value
   Flask receives through Cloudflare -> Railway -> Gunicorn, and whether direct
   custom headers survive.
2. Add production `TRUSTED_HOSTS` for the apex, `www`, and only the Railway or
   health-check hosts that are genuinely required. Keep local hosts explicit in
   the local runner/tests.
3. Prefer Cloudflare for browser HTTPS redirects. Retain the application hook
   only as a direct-origin fallback with a documented trusted-header contract.
4. If `ProxyFix` is introduced, trust only the exact header types and hop count
   Railway documents. Do not copy a blanket `x_for=x_host=x_proto=1` example.

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
and included a Railway marker, proving they did not pass through the current
Flask `after_request` hook. The exact upstream component issuing the redirect
should still be confirmed in the dashboards.

**Actual risk**

Users are redirected today, but enforcement ownership is implicit and there is
no browser memory of the HTTPS requirement. The first HTTP request remains
subject to downgrade until HSTS has been learned. Enabling HSTS prematurely can
make hostnames inaccessible if their HTTPS support later fails.

**Recommended target and migration order**

1. Inventory apex, `www`, any public Railway hostname, and every subdomain that
   could be affected by future `includeSubDomains`.
2. Confirm current HTTPS and redirect behavior for apex and `www` and identify
   the present redirect owner.
3. Enable Cloudflare **Always Use HTTPS** so the public edge is the explicit
   enforcement point. Re-test path and query preservation.
4. Keep the Flask redirect as an optional direct-origin fallback only after F5
   is resolved.
5. After a stable observation period, enable Cloudflare HSTS with a short
   `max-age`, without `includeSubDomains` and without preload.
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

### F8. Existing browser headers are application-owned but incomplete

**Status:** confirmed  
**Priority:** Low outside the CSP/HSTS findings  
**Enforcement layer:** Dash/Flask application

**Current state and evidence**

`app/server_hooks.py` sets:

- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `X-Frame-Options: SAMEORIGIN`

The exact same values appeared on HTML, static asset, Dash JSON, and reload
responses, so their origin is confirmed as Flask rather than Cloudflare or
Railway. `Permissions-Policy` is absent.

**Actual risk**

The present values are suitable. The app does not use camera, microphone, or
geolocation, so those browser capabilities remain unnecessarily available by
default. Framing is already limited; CSP `frame-ancestors 'self'` should become
the modern paired control.

**Recommended mitigation**

Add and test a narrow application-owned policy such as:

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

**Status:** confirmed positive control with a low-priority process gap  
**Priority:** Low  
**Enforcement layer:** repository and deployment supply chain

**Current state and evidence**

`uv.lock` resolves 48 packages, with 47 registry packages and no VCS or direct
URL dependency. Runtime versions observed in production for Dash and Plotly
match the lock. Registry artifacts carry lockfile hashes. A current advisory
scan reported no application-package vulnerability.

The local environment's `pip==26.1.1` advisory is not represented in
`uv.lock`; it is tooling/build-environment hygiene, not evidence of a vulnerable
import in the deployed app.

**Actual risk**

The resolved application environment is reproducible, but a new advisory can
remain unnoticed between manual audits. Broad direct requirements in
`pyproject.toml` also make an intentional lock refresh capable of selecting
new major versions, even though ordinary locked installs remain deterministic.

**Recommended mitigation**

- Verify Railway installs from `uv.lock` in frozen/locked mode; the matching
  live versions are supporting evidence but not build-log proof.
- Add a repeatable runtime export plus `pip-audit` check to the development or
  CI workflow when such automation is introduced.
- Upgrade the local environment's pip tooling to a fixed version without adding
  `pip` as an application dependency.
- Keep dependency upgrades separate from CSP enforcement unless a security fix
  requires coupling them.

### F11. Production debug mode is not exposed; exception text still reaches browser state

**Status:** confirmed positive debug control and low-priority information-disclosure finding  
**Priority:** Low  
**Enforcement layer:** Dash/Flask application and Railway deployment variables

**Current state**

`DASH_DEBUG` defaults false and is used only inside the
`if __name__ == '__main__'` local runner. Gunicorn imports
`pendulum_app:server`, so that block cannot run in production. Live Dash config
showed development UI and property checks disabled, and hot reload inactive.

Simulation exception handlers catch broad exceptions but put `str(exc)` into
the failed Canvas payload's `errors` collection, which is sent to the browser.
No traceback was observed, and no secrets are configured.

**Actual risk**

There is no exposed Werkzeug/Dash debugger. Crafted solver failures may still
reveal library messages or implementation details useful for reconnaissance.
The impact is low because the application is public, stateless, and contains no
credentialed backend.

**Recommended mitigation**

Return stable public error codes/messages and log exception details server-side
with a request correlation identifier. Keep numerical diagnostics that are
deliberately educational, but separate them from raw exception text. Verify
Railway does not set local-only debug variables; changing `DASH_DEBUG` currently
does not affect Gunicorn import, but deployment variables should still reflect
intent.

### F12. External-link opener handling is inconsistent

**Status:** confirmed low-impact finding  
**Priority:** Low / opportunistic  
**Enforcement layer:** application markup

**Current state and evidence**

Home and footer links opened with `target="_blank"` also set
`rel="noopener noreferrer"`. Reference links created by
`app/components/references.py` use `_blank` without an explicit `rel`.

**Actual risk**

Modern browsers implicitly apply `noopener` to `_blank`, so this is not a
meaningful exploit on current browsers. Explicit consistency protects older or
embedded clients and makes intent reviewable.

**Recommended mitigation**

Add `rel="noopener noreferrer"` to reference links during a small application
hardening pass. Do not make this a CSP blocker.

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

## Recommended target state

### Application

- CSP module with explicit modes, validated Dash hashes, and tests.
- CSP configured after all clientside callbacks are registered.
- Per-response CSP nonce compatible with Cloudflare JavaScript Detections.
- Initial enforced policy has no unsafe script/eval and retains only the
  documented inline-style allowance.
- `TRUSTED_HOSTS` configured by deployment mode.
- Narrow `Permissions-Policy`.
- Measured request-body cap, finite/enum validation, and generic public solver
  errors.
- Existing low-risk headers retained.

### Railway/deployment

- Gunicorn remains the production server; debug variables remain off.
- Worker/concurrency settings are explicit only after memory and request-cost
  measurements.
- Locked dependency installation is verified from build logs.
- Custom-domain status, origin certificate behavior, and any Railway-generated
  public hostname are inventoried.
- Full remains the supported Cloudflare-to-Railway TLS mode unless Railway
  confirms a strictly validated alternative.

### Cloudflare

- Existing scanner rule retained at the edge.
- JavaScript Detections retained and verified with the application nonce.
- Callback rate limiting observed and then enforced at the edge.
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
- HSTS is delivered only after the HTTPS migration checks.

## Proposed sequence of small implementation passes

### Pass 0: deployment fact verification

- Record Railway `FORCE_HTTPS` and debug variables.
- Identify the current HTTP redirect owner.
- Inventory apex, `www`, Railway hostnames, health checks, and direct-origin
  reachability.
- Confirm Cloudflare JavaScript Detections is intentionally enabled.
- Confirm Railway domain/certificate status and locked build behavior.
- Measure representative callback request sizes and compute cost.

No behavior change.

### Pass 1: low-risk application guards

- Add production/local `TRUSTED_HOSTS` configuration and tests.
- Add `Permissions-Policy`.
- Add explicit enum and finite-number validation.
- Add `rel` to reference links.
- Replace raw public exception strings with stable messages.
- Add a measured request-body limit.

Deploy and verify before CSP.

### Pass 2: CSP scaffolding, initially off or report-only

- Add a dedicated policy builder and mode parser.
- Move server-hook configuration after all callback registration.
- Capture and validate `app.csp_hashes()`.
- Add the per-response nonce design.
- Add unit/integration tests for exact directives and modes.
- Keep the inline-style limitation explicit.

Do not enforce in production in this pass.

### Pass 3: production CSP report-only observation

- Deploy `Content-Security-Policy-Report-Only`.
- Verify Cloudflare adds the advertised nonce to its injected bootstrap.
- Exercise all public routes, dynamic navigation, MathJax, Canvas playback,
  invalid inputs, and callback requests.
- Inspect console/report data for unexpected origins, eval, workers, images,
  fonts, connections, and style behavior.
- Keep a tested `off` rollback.

### Pass 4: CSP enforcement

- Enforce the observed policy with no unsafe script/eval.
- Retain `style-src 'unsafe-inline'` as the only unsafe source.
- Re-run browser and server tests through Cloudflare.
- Optionally move the two clientside callback functions into a namespaced asset
  later; this reduces release-coupled hashes but is not required for first
  enforcement because Dash's renderer bootstrap still needs handling.

### Pass 5: availability and origin controls

- Add an observed-then-enforced Cloudflare callback rate limit.
- Decide whether the direct Railway hostname can be disabled.
- If necessary, stage a Cloudflare-overwritten origin secret with an
  application rollback.
- Tune Gunicorn only from Railway memory and concurrency evidence.

These controls should not be bundled into the CSP deployment.

### Pass 6: HTTPS and HSTS edge migration

- Keep Cloudflare/Railway Full while provider guidance requires it.
- Enable **Always Use HTTPS** and verify both hostnames, paths, and queries.
- Introduce short HSTS without subdomains/preload, observe, then increase.
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
- Cloudflare JavaScript Detections and CSP nonce propagation:
  <https://developers.cloudflare.com/cloudflare-challenges/challenge-types/javascript-detections/>
- Cloudflare CSP product interactions:
  <https://developers.cloudflare.com/fundamentals/reference/policies-compliances/content-security-policies/>
- Cloudflare HSTS requirements and rollout cautions:
  <https://developers.cloudflare.com/ssl/edge-certificates/additional-options/http-strict-transport-security/>

