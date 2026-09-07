---
title: Session cookies
module: authentication
status: reviewed
reviewed: 2026-09-07
tags: [Authentication, Sessions, Cookies]
sources:
  - { type: standard, name: "RFC 6265bis — Cookies: HTTP State Management Mechanism (draft)", url: "https://datatracker.ietf.org/doc/html/draft-ietf-httpbis-rfc6265bis" }
  - { type: standard, name: "OWASP Session Management Cheat Sheet", url: "https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html" }
  - { type: vendor, name: "Microsoft Learn — Microsoft Entra Conditional Access overview", url: "https://learn.microsoft.com/en-us/entra/identity/conditional-access/overview" }
---

# Session cookies

## Executive summary

### Purpose

A session cookie holds an opaque identifier that maps, server-side, to
session state — who is logged in, when the session started, what it is
allowed to do. The browser stores and resends the cookie automatically per
[RFC 6265bis](https://datatracker.ietf.org/doc/html/draft-ietf-httpbis-rfc6265bis)
(the IETF's still-in-progress successor to RFC 6265, cited here as the
current draft cookie specification, not a published RFC), and the
application looks the identifier up against a session store on every
request. Unlike a [JWT](jwt.md), the token itself carries no claims — all
state lives server-side, which is exactly what makes it revocable.

### When to use

Use session cookies as the default for browser-facing applications: the
[JWT vs session cookies matrix](../../matrices/jwt-vs-session-cookies.md)
rates them the "best fit" for exactly this case, because the browser
handles storage and transmission natively and the `HttpOnly` flag keeps
the identifier out of reach of page scripts entirely — something no
client-side JWT storage strategy can claim outright.

### When not to use

- The consumer is not a browser — a mobile app calling an API, a
  service-to-service integration, a CLI. There is no cookie jar and no
  automatic same-origin transmission to rely on; use a
  [JWT](jwt.md) or [OAuth 2.0](oauth2.md) access token instead.
- The application is horizontally scaled across many stateless instances
  with no shared session store, and adding one is not acceptable. The
  matrix rates session cookies as "needs shared session store" — a real
  operational cost a stateless JWT avoids.
- The request needs to cross origins where cookies are blocked or
  stripped by default (some third-party embedded contexts, certain
  `SameSite` configurations) — see Common mistakes below on setting
  `SameSite` correctly rather than routing around cookies entirely for
  same-site cases.

## How it works

``` mermaid
sequenceDiagram
  autonumber
  actor User
  participant App as Application
  participant Store as Session store
  User->>App: POST /login (credentials)
  App->>App: verify credentials (see email-password.md)
  App->>App: generate cryptographically random session ID
  App->>Store: create session record (user id, created at, expiry)
  App-->>User: Set-Cookie: sid=<id>; HttpOnly; Secure; SameSite=Lax
  User->>App: GET /resource (Cookie: sid=<id>)
  App->>Store: look up session by id
  Store-->>App: session record (or not found)
  alt session found and not expired
    App-->>User: 200 + resource
  else session missing or expired
    App-->>User: 401, clear cookie
  end
  User->>App: POST /logout
  App->>Store: delete session record
  App-->>User: Set-Cookie: sid=; Max-Age=0 (immediate invalidation)
```

## Pros and cons

- **Pro**: logout and revocation are immediate — delete the server-side
  record and the identifier is worthless on the very next request. The
  [JWT vs session cookies matrix](../../matrices/jwt-vs-session-cookies.md)
  rates this "immediate" against a JWT's need for "a denylist."
- **Pro**: `HttpOnly` keeps the session identifier unreadable to page
  JavaScript, closing the exact exposure path the [JWT
  localStorage mistake](jwt.md#common-mistakes) describes.
- **Con**: requires server-side state — a session store every application
  instance can reach — which is real infrastructure a stateless token
  does not need, per the matrix's "needs shared session store" row.
- **Con**: does not travel naturally to non-browser clients; a mobile app
  or CLI has no cookie jar participating in the same-origin cookie model.

## Alternatives

- **[JWT](jwt.md)** trades revocability for statelessness — appropriate
  for API and service-to-service access rather than browser sessions; see
  the [decision matrix](../../matrices/jwt-vs-session-cookies.md) for the
  full tradeoff.
- **[Refresh tokens](refresh-tokens.md)** solve a related but distinct
  problem — bounding a long-lived credential's exposure — and often sit
  alongside session cookies for mixed browser/API applications.

## Security considerations

- [Session security](../../security/session-security.md) — cookie flags,
  fixation, rotation on privilege change; the primary hardening reference
  for everything on this page.
- [Rate limiting](../../security/rate-limiting.md) — throttling login
  endpoints that mint new sessions.
- [MFA](../../security/mfa.md) — what a session should require before
  granting access to sensitive actions.

See the [JWT vs session cookies matrix](../../matrices/jwt-vs-session-cookies.md)
for when to choose this mechanism over a token, and run new session logic
against the [authentication checklist](../../checklists/authentication.md).

## Implementation examples

- **Set all three cookie flags**: per
  [RFC 6265bis](https://datatracker.ietf.org/doc/html/draft-ietf-httpbis-rfc6265bis)
  and the OWASP Session Management Cheat Sheet, issue the session cookie
  with `HttpOnly` (unreadable to JavaScript), `Secure` (sent only over
  TLS), and an explicit `SameSite` value (`Lax` for most applications,
  `Strict` for the most sensitive ones) rather than relying on browser
  defaults.
- **Generate the session identifier with a CSPRNG**: the OWASP Session
  Management Cheat Sheet requires session IDs to be generated by the
  platform's cryptographically secure random number generator, with
  enough entropy that guessing or brute-forcing one is infeasible.
- **Regenerate the session ID on privilege change**: issue a new session
  identifier at login and again on any privilege escalation (for example,
  completing MFA), invalidating the old one — this defeats session
  fixation, where an attacker seeds a victim's browser with a known
  session ID before authentication.
- **Set an absolute and an idle timeout**: expire sessions after a fixed
  maximum lifetime regardless of activity, and separately after a period
  of inactivity, per the OWASP Session Management Cheat Sheet's timeout
  guidance — the [module overview](index.md#non-functional-requirements)
  sets an 8-hour idle timeout as this playbook's default.

## Common mistakes

### Omitting `HttpOnly`, `Secure`, or `SameSite`

A session cookie set without `HttpOnly` is readable by any script on the
page, collapsing the exact protection session cookies are supposed to have
over a JWT stored in `localStorage`. Without `Secure`, the cookie can be
sent over plaintext HTTP if the app is ever reached that way. Without an
explicit `SameSite`, browser defaults vary and cross-site request forgery
exposure is harder to reason about. Set all three explicitly on every
session cookie, per RFC 6265bis and the OWASP Session Management Cheat
Sheet.

### Not regenerating the session ID after login

If the session identifier issued before authentication stays valid after
it, an attacker who can plant a known session ID in a victim's browser
(session fixation) simply waits for the victim to log in under that ID and
inherits the authenticated session. The OWASP Session Management Cheat
Sheet requires regenerating the session ID at authentication and at any
privilege level change. Always issue a fresh identifier post-login and
invalidate the pre-login one.

### Relying on client-side expiry alone

A cookie's `Max-Age` or `Expires` attribute only controls when the
browser stops sending it — it does nothing to invalidate the
corresponding record server-side. A session store entry left alive past
its intended lifetime, or never checked against an absolute timeout, stays
usable if the cookie is somehow replayed (a proxy log, a captured
request) after the browser would have discarded it. Enforce both absolute
and idle timeouts against the server-side record, not just the cookie's
client-side attributes.

## Real-world implementations

- **Microsoft Entra** issues browser session cookies for its sign-in
  experience and layers [Conditional
  Access](https://learn.microsoft.com/en-us/entra/identity/conditional-access/overview)
  policies "enforced after first-factor authentication is completed,"
  re-checking device and risk signals against the active session rather
  than trusting the cookie's mere presence indefinitely — the same
  ongoing-verification posture this page's timeout guidance encodes.

## References

<!-- generated:references start -->
| Type | Source |
| --- | --- |
| Standard | [RFC 6265bis — Cookies: HTTP State Management Mechanism (draft)](https://datatracker.ietf.org/doc/html/draft-ietf-httpbis-rfc6265bis) |
| Standard | [OWASP Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html) |
| Vendor | [Microsoft Learn — Microsoft Entra Conditional Access overview](https://learn.microsoft.com/en-us/entra/identity/conditional-access/overview) |
<!-- generated:references end -->

<!-- generated:page-footer start -->
**Status:** reviewed · **Last reviewed:** 2026-09-07 · **Review due:** 2027-03-06
<!-- generated:page-footer end -->
