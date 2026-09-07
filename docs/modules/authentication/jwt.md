---
title: JWT
module: authentication
status: reviewed
reviewed: 2026-09-07
tags: [Authentication, JWT, Tokens]
sources:
  - { type: rfc, name: "RFC 7519 — JSON Web Token (JWT)", url: "https://www.rfc-editor.org/rfc/rfc7519" }
  - { type: standard, name: "OWASP JSON Web Token Cheat Sheet", url: "https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_Cheat_Sheet.html" }
  - { type: rfc, name: "RFC 8725 — JSON Web Token Best Current Practices", url: "https://www.rfc-editor.org/rfc/rfc8725" }
  - { type: vendor, name: "GitHub Docs — Managing your personal access tokens", url: "https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens" }
---

# JWT

## Executive summary

### Purpose

A JSON Web Token (JWT) is, per
[RFC 7519](https://www.rfc-editor.org/rfc/rfc7519)'s Abstract, "a compact,
URL-safe means of representing claims to be transferred between two
parties." A JWT is a signed (and optionally encrypted) set of claims — who
issued it, who it is for, when it expires, and any application-specific
data — that a recipient can verify without calling back to the issuer.
That self-contained, statelessly verifiable property is the entire reason
to reach for a JWT instead of an opaque session identifier, and it is also
the source of everything hard about revoking one.

### When to use

Use a JWT as an access token for service-to-service calls or API access
where the verifying party (a resource server, a microservice) should not
need a network round trip to a central session store on every request, and
where the token's lifetime can be kept short. This is the access-token
half of the [OAuth 2.0](oauth2.md) and [OIDC](oidc.md) flows on this
module's other pages, and the stateless side of the token-model choice the
[module overview](index.md#alternatives) frames as JWT vs. session
cookies.

### When not to use

- The client is a browser-based single-page app and the natural storage
  location is `localStorage` or `sessionStorage`. See Common mistakes
  below — this is the single most consequential misuse this page exists
  to prevent.
- The application needs immediate, server-enforced logout or revocation.
  Per the [JWT vs session cookies matrix](../../matrices/jwt-vs-session-cookies.md),
  a JWT is "valid until expiry" with revocation rated "hard," because
  invalidating one before its `exp` claim requires maintaining a denylist —
  the exact server-side state a stateless token was meant to avoid. Use a
  [session cookie](session-cookies.md) when logout must take effect
  immediately.
- The claims payload needs to change frequently (role changes, permission
  updates) and those changes must apply before the token's natural
  expiry. A JWT's claims are frozen at issuance; use a
  [session cookie](session-cookies.md) backed by server-side state
  instead — the matrix rates it as "needs shared session store," but that
  state is exactly what lets it reflect changes immediately.

## How it works

``` mermaid
sequenceDiagram
  autonumber
  actor Client
  participant Auth as Authorization/Auth server
  participant RS as Resource server
  Client->>Auth: authenticate (see oauth2.md / oidc.md)
  Auth->>Auth: build claims (iss, sub, aud, exp, iat, custom)
  Auth->>Auth: sign with private key (e.g. RS256) or shared secret (HS256)
  Auth-->>Client: JWT (header.payload.signature)
  Client->>RS: request with Authorization: Bearer <JWT>
  RS->>RS: verify signature against known key/algorithm
  RS->>RS: check exp, nbf, iss, aud
  alt valid and not expired
    RS-->>Client: authorized response
  else invalid, expired, or wrong audience
    RS-->>Client: 401
  end
```

## Pros and cons

- **Pro**: self-contained and statelessly verifiable — a resource server
  can check signature, `exp`, and `aud` locally with no call back to an
  auth service, which is what makes JWTs attractive for
  horizontally-scaled APIs; the
  [JWT vs session cookies matrix](../../matrices/jwt-vs-session-cookies.md)
  rates this "no shared store needed."
- **Pro**: standardized claim names (`iss`, `sub`, `aud`, `exp`, `nbf`,
  `iat`) mean interoperating systems agree on the shape of the token
  without custom negotiation.
- **Con**: cannot be revoked before `exp` without introducing the
  server-side state (a denylist) the format was chosen to avoid — the
  matrix rates JWT revocation "hard" against a session cookie's "easy."
- **Con**: payload size grows with every claim added, unlike an opaque
  session identifier, and that payload rides along on every request as an
  HTTP header.
- **Con**: an unverified read of the payload is trivially available to
  anyone holding the token — the payload is base64url-encoded, not
  encrypted, unless you specifically use JWE. Do not put secrets in JWT
  claims.

## Alternatives

- **[Session cookies](session-cookies.md)** trade statelessness for
  instant revocation and simpler logout semantics — the right default for
  browser-facing applications per the
  [JWT vs session cookies matrix](../../matrices/jwt-vs-session-cookies.md).
- **[Refresh tokens](refresh-tokens.md)** pair with short-lived JWTs to
  bound the exposure window of a token that cannot itself be revoked.
- **Opaque tokens with introspection** (an OAuth 2.0 token introspection
  endpoint) keep a JWT-like bearer-token model but restore the
  revocation-check round trip a JWT was designed to skip — a middle
  ground when both statelessness and revocability matter.

## Security considerations

This page states the mechanism; hardening detail lives in
[docs/security/](../../security/index.md):

- [OAuth security](../../security/oauth-security.md) — token issuance and
  scope validation for JWTs used as OAuth access tokens.
- [Session security](../../security/session-security.md) — compare
  against the cookie-based model directly; see the
  [JWT vs session cookies matrix](../../matrices/jwt-vs-session-cookies.md)
  for the tradeoff this page and that page must not contradict.
- [Secrets management](../../security/secrets-management.md) — protecting
  the signing key or secret itself; a leaked signing key lets an attacker
  mint arbitrary valid tokens.

Run any new JWT-issuing surface against the
[authentication checklist](../../checklists/authentication.md).

## Implementation examples

- **Always verify, never just decode**: per the OWASP JSON Web Token
  Cheat Sheet, an application must cryptographically verify a JWT's
  signature before trusting any claim inside it — a library call that
  merely base64-decodes the payload is not a security check.
- **Pin the expected algorithm**: [RFC 8725](https://www.rfc-editor.org/rfc/rfc8725)
  (JWT Best Current Practices) warns against trusting an algorithm named
  in the token's own header; configure the verifier with the specific
  expected algorithm (for example `RS256`) rather than accepting whatever
  `alg` the token claims, which closes the classic "`alg: none`" and
  algorithm-confusion attacks.
- **Set short expiries and validate `aud`**: keep access-token JWTs
  short-lived (minutes, not days) since they cannot be revoked, and always
  check `aud` so a token minted for one resource server cannot be replayed
  against another.
- **Use asymmetric signing when multiple parties verify the token**: with
  `RS256` or `ES256`, the resource server needs only the public key to
  verify, so the signing key never has to be distributed to every
  verifier the way an `HS256` shared secret would.

## Common mistakes

### Storing a JWT in `localStorage`

Any script running on the page can read `localStorage`. A single XSS flaw
therefore yields a bearer token that works from anywhere until it expires,
and you cannot revoke it.

Store the token in an `HttpOnly`, `Secure`, `SameSite` cookie, or keep it in
memory only and rely on a refresh token in an `HttpOnly` cookie.

### Trusting the `alg` header the token itself supplies

If a verifier picks its verification algorithm from the token's own
`alg` field, an attacker can submit a token claiming `alg: none` or swap
an asymmetric algorithm for a symmetric one, tricking some libraries into
verifying a forged token against a public key they treat as a shared
secret. RFC 8725 calls this out directly as a known class of JWT
vulnerability. Configure the verifier with an explicit, fixed expected
algorithm and reject anything else.

### Putting sensitive data in the payload

A JWT's payload is base64url-encoded, not encrypted — anyone holding the
token, including a client-side script or a logging pipeline that captures
request headers, can read every claim. RFC 7519 §4 defines the payload as
the "JWT Claims Set," a JSON object whose members are the claims conveyed
by the token — it is a transport structure, not a container designed for
secrecy. Keep sensitive data (raw passwords, full PII beyond what the
resource server strictly needs) out of the claims, and use JWE if the
payload genuinely must be confidential from the bearer.

## Real-world implementations

- **GitHub** issues short-lived, narrowly scoped
  [personal access tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)
  and app-installation tokens rather than one long-lived unrevocable
  credential — the practical version of the same short-lifetime,
  narrow-scope principle that makes an unrevocable JWT tolerable in
  production.

## References

<!-- generated:references start -->
| Type | Source |
| --- | --- |
| RFC | [RFC 7519 — JSON Web Token (JWT)](https://www.rfc-editor.org/rfc/rfc7519) |
| Standard | [OWASP JSON Web Token Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_Cheat_Sheet.html) |
| RFC | [RFC 8725 — JSON Web Token Best Current Practices](https://www.rfc-editor.org/rfc/rfc8725) |
| Vendor | [GitHub Docs — Managing your personal access tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens) |
<!-- generated:references end -->

<!-- generated:page-footer start -->
**Status:** reviewed · **Last reviewed:** 2026-09-07 · **Review due:** 2027-03-06
<!-- generated:page-footer end -->
