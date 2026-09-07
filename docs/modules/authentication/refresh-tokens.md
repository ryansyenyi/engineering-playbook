---
title: Refresh tokens
module: authentication
status: reviewed
reviewed: 2026-09-07
tags: [Authentication, Tokens, OAuth]
sources:
  - { type: rfc, name: "RFC 6749 §1.5 — The OAuth 2.0 Authorization Framework: Refresh Token", url: "https://www.rfc-editor.org/rfc/rfc6749#section-1.5" }
  - { type: standard, name: "OAuth 2.0 Security Best Current Practice (IETF Internet-Draft)", url: "https://datatracker.ietf.org/doc/html/draft-ietf-oauth-security-topics" }
  - { type: vendor, name: "Auth0 Docs — Refresh Token Rotation", url: "https://auth0.com/docs/secure/tokens/refresh-tokens/refresh-token-rotation" }
---

# Refresh tokens

## Executive summary

### Purpose

A refresh token is a long-lived credential exchanged for a new access
token without requiring the user to log in again. [RFC 6749 §1.5](https://www.rfc-editor.org/rfc/rfc6749#section-1.5)
defines refresh tokens as "credentials used to obtain access tokens," and
states that they "are issued to the client by the authorization server
and are used to obtain a new access token when the current access token
becomes invalid or expires..." It exists specifically so that access
tokens — including [JWTs](jwt.md) —
can be kept short-lived without forcing constant re-authentication; the
refresh token absorbs the long-lived risk so the access token does not
have to.

### When to use

Use refresh tokens whenever you issue short-lived access tokens — the
[JWT](jwt.md) page's recommendation to keep access-token lifetimes to
minutes, not days — and need the client to stay signed in longer than
that without re-prompting for credentials. This is standard for mobile
apps and single-page applications built on [OAuth 2.0](oauth2.md) or
[OIDC](oidc.md).

### When not to use

- The access token's lifetime is already short enough that
  re-authentication on expiry is acceptable — a low-value, low-frequency
  integration may not need the added complexity of rotation and reuse
  detection at all.
- The client cannot securely store a long-lived secret at all — a public
  client with no secure storage (some browser contexts) turns a leaked
  refresh token into a standing compromise; confine refresh tokens to
  clients that can protect them, and rely on shorter
  [session cookies](session-cookies.md) for the ones that cannot.
- The system is a pure server-to-server integration using the client
  credentials grant, where there is no end user session to keep alive and
  the client can simply re-authenticate with its own credentials on
  demand.

## How it works

The flow below matches the [module overview's rotation
diagram](index.md#flow-diagram): every refresh token is part of a family,
each use retires it and issues a successor, and replaying an already-used
token revokes the whole family rather than just rejecting the one request.

``` mermaid
sequenceDiagram
  autonumber
  participant Client
  participant Auth as Authorization server
  participant Store as Token store (families)
  Client->>Auth: POST /token (grant_type=refresh_token, refresh_token)
  Auth->>Store: look up token family by token id
  alt token already marked used
    Store-->>Auth: reuse detected
    Auth->>Store: revoke entire family
    Auth-->>Client: 401 (reuse detected, re-authenticate)
  else token valid and unused
    Store-->>Auth: family record
    Auth->>Store: mark this token used, issue successor
    Auth-->>Client: new access token (short-lived) + new refresh token
  end
```

## Pros and cons

- **Pro**: lets access tokens stay short-lived — minutes rather than
  days — without forcing the user to log in again on every expiry, which
  is what makes an unrevocable [JWT](jwt.md) access token tolerable in
  practice.
- **Pro**: rotation with reuse detection turns a captured refresh token
  into a detectable event rather than a silent, indefinite compromise: the
  moment the legitimate client's next rotation collides with an
  attacker's earlier use, the family is revoked.
- **Con**: is itself a long-lived bearer credential until rotated or
  revoked, so its storage matters as much as an access token's — a
  refresh token leaked from client storage is a standing risk until it is
  next used or expires.
- **Con**: rotation and family tracking require server-side state (the
  token store above), which is exactly the kind of infrastructure a
  stateless-token approach was trying to avoid; see the
  [JWT vs session cookies matrix](../../matrices/jwt-vs-session-cookies.md)
  for the same tradeoff applied to access tokens.

## Alternatives

- **Longer-lived access tokens with no refresh token** avoid the added
  rotation machinery, at the cost of a wider exposure window if the access
  token itself leaks — generally the wrong tradeoff once the token is a
  bearer [JWT](jwt.md) that cannot be revoked.
- **[Session cookies](session-cookies.md)** sidestep the whole
  refresh-token problem for browser-facing apps by keeping session state
  server-side and revocable directly, per the
  [decision matrix](../../matrices/jwt-vs-session-cookies.md).
- **Re-authentication on expiry** (no refresh token at all) is simplest
  and appropriate when the access token's lifetime is already acceptable
  for the product's session-length expectations.

## Security considerations

- [OAuth security](../../security/oauth-security.md) — refresh tokens are
  issued and exchanged through the same token endpoint as access tokens;
  the redirect and client-authentication hardening there applies here too.
- [Session security](../../security/session-security.md) — treat a
  refresh token with at least the same storage discipline as a session
  identifier.
- [Secrets management](../../security/secrets-management.md) — refresh
  tokens are long-lived secrets and belong in secure storage, not
  `localStorage` or an unencrypted mobile preference store.

Validate rotation and reuse-detection logic against the
[authentication checklist](../../checklists/authentication.md) before
shipping it.

## Implementation examples

- **Rotate on every use**: issue a new refresh token every time one is
  redeemed and invalidate the one just used, rather than allowing the same
  refresh token to be exchanged repeatedly — the OAuth 2.0 Security Best
  Current Practice document (still an IETF Internet-Draft,
  `draft-ietf-oauth-security-topics`, not yet a published RFC) recommends
  rotation specifically to limit the window in which a stolen token
  remains useful.
- **Detect and act on reuse**: track refresh tokens as members of a
  family (all descendants of one original login). If a token that has
  already been marked used is presented again, treat it as evidence of
  theft — the legitimate client already moved on to the successor — and
  revoke every token in that family, forcing full re-authentication.
- **Bind refresh tokens to the client** where the client type allows it
  (confidential clients, or public clients with device attestation), so a
  token stolen from one client context cannot be redeemed from another.
- **Set an absolute lifetime even with rotation**: rotation limits the
  blast radius of a single theft, but an indefinitely rotating chain still
  keeps a session alive forever. Cap the total family lifetime and require
  full re-authentication after it, independent of how recently the token
  was rotated.

## Common mistakes

### Allowing a refresh token to be reused without detection

If a refresh token stays valid across multiple redemptions instead of
being retired on first use, a token captured once — through a log leak, a
network intercept, or a compromised device — grants an attacker ongoing
parallel access alongside the legitimate user, with no signal to either
party that anything is wrong. The OAuth 2.0 Security Best Current Practice
recommends rotation with reuse detection precisely to close this gap.
Rotate on every use and revoke the entire family the instant a used token
is replayed, exactly as the flow diagram above shows.

### Treating a rotated refresh token family as permanent

Rotation with reuse detection catches a stolen token being replayed after
the legitimate client has already moved on — it does nothing if the
attacker's copy is used first and the legitimate client's is the one that
gets treated as the replay, or if a family simply rotates forever without
ever requiring fresh credentials. Cap the family's absolute lifetime and
force full re-authentication when it is reached, rather than assuming
rotation alone bounds risk indefinitely.

### Storing a refresh token the same way you would a short-lived access token

A refresh token typically outlives an access token by orders of magnitude
and is exactly as much a bearer credential. Storing it in `localStorage`
on a browser client exposes it to the same XSS-driven theft the
[JWT localStorage mistake](jwt.md#common-mistakes) describes, except the
exposure window is the refresh token's much longer lifetime rather than a
short-lived access token's. Store it server-side (in an `HttpOnly`
cookie or a secure backend session) wherever the client architecture
allows it.

## Real-world implementations

- **Auth0** implements [refresh token
  rotation](https://auth0.com/docs/secure/tokens/refresh-tokens/refresh-token-rotation)
  as the recommended default for public clients such as native and
  single-page applications — the client type that cannot hold a
  confidential client secret — issuing a new refresh token on every
  exchange and automatically revoking the family when a rotated-out token
  is reused — the same family-revocation behavior the flow diagram on this
  page
  documents.

## References

<!-- generated:references start -->
| Type | Source |
| --- | --- |
| RFC | [RFC 6749 §1.5 — The OAuth 2.0 Authorization Framework: Refresh Token](https://www.rfc-editor.org/rfc/rfc6749#section-1.5) |
| Standard | [OAuth 2.0 Security Best Current Practice (IETF Internet-Draft)](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-security-topics) |
| Vendor | [Auth0 Docs — Refresh Token Rotation](https://auth0.com/docs/secure/tokens/refresh-tokens/refresh-token-rotation) |
<!-- generated:references end -->

<!-- generated:page-footer start -->
**Status:** reviewed · **Last reviewed:** 2026-09-07 · **Review due:** 2027-03-06
<!-- generated:page-footer end -->
