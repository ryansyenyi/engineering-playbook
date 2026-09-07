---
title: JWT vs session cookies
module: authentication
status: reviewed
reviewed: 2026-09-07
tags: [Decision matrix, Authentication, Security]
sources:
  - { type: rfc, name: "RFC 7519 — JSON Web Token", url: "https://www.rfc-editor.org/rfc/rfc7519" }
  - { type: standard, name: "OWASP Session Management Cheat Sheet", url: "https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html" }
---

# JWT vs session cookies

<!-- generated:matrix start -->
| Criterion | JWT (stateless) | Session cookie (server state) |
| --- | --- | --- |
| Revocation | Hard — token valid until expiry | Easy — delete the session |
| Horizontal scale | No shared store needed | Needs shared session store |
| Payload size | Grows with claims | Opaque identifier only |
| XSS exposure | High if stored in localStorage | Low with HttpOnly |
| Logout semantics | Needs a denylist | Immediate |
| Best fit | Short-lived service-to-service | Browser-facing applications |
<!-- generated:matrix end -->

## Why

The decision is about revocation, not about tokens. A JWT is a bearer
credential you cannot take back before it expires; a session identifier is a
lookup you can delete. Everything else follows from that.

## Tradeoffs

Statelessness buys horizontal scale and costs you immediate logout. Most
applications that adopt JWTs then rebuild session state as a denylist, which
is the state they were avoiding, with worse ergonomics.

## Migration path

Shorten the access token lifetime first, then introduce refresh tokens with
rotation, then move browser-facing sessions to `HttpOnly` cookies.

## References

<!-- generated:references start -->
| Type | Source |
| --- | --- |
| RFC | [RFC 7519 — JSON Web Token](https://www.rfc-editor.org/rfc/rfc7519) |
| Standard | [OWASP Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html) |
<!-- generated:references end -->

<!-- generated:page-footer start -->
**Status:** reviewed · **Last reviewed:** 2026-09-07 · **Review due:** 2027-03-06
<!-- generated:page-footer end -->
