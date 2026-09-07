---
title: OAuth 2.0
module: authentication
status: reviewed
reviewed: 2026-09-07
tags: [Authentication, OAuth]
sources:
  - { type: rfc, name: "RFC 6749 — The OAuth 2.0 Authorization Framework", url: "https://www.rfc-editor.org/rfc/rfc6749" }
  - { type: rfc, name: "RFC 7636 — Proof Key for Code Exchange (PKCE)", url: "https://www.rfc-editor.org/rfc/rfc7636" }
  - { type: vendor, name: "GitHub Docs — Authorizing OAuth Apps (device flow)", url: "https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps" }
---

# OAuth 2.0

## Executive summary

### Purpose

OAuth 2.0 is an authorization framework: it lets a third-party application
obtain limited access to a resource on a user's behalf, without that
application ever seeing the user's credentials for the resource owner.
[RFC 6749](https://www.rfc-editor.org/rfc/rfc6749) defines four roles —
resource owner, client, authorization server, resource server — and a set
of grant types that produce an access token the client presents to the
resource server. It is the delegation mechanism underneath both
[social login](social-login.md) and [OIDC](oidc.md); OAuth 2.0 itself
answers what a client can *do*, not who the user *is*.

### When to use

Use OAuth 2.0 when a client — a web app, a mobile app, a CLI, a
server-to-server integration — needs scoped access to a resource hosted by
a separate authorization server, and you want to avoid that client ever
holding the resource owner's password. This is the mechanism underneath
"Connect your Google Drive" or "Authorize this CLI against our API"
integrations.

### When not to use

- The goal is to establish who the user is, not what they can access. OAuth
  2.0 has no standardized identity assertion; per RFC 6749 the access token
  is scoped to resource access, nothing more. Use [OIDC](oidc.md), which
  layers an identity token on top of this exact flow, when authentication
  is the actual requirement.
- The client is a single first-party application talking to its own
  backend with no third-party resource involved. A direct
  [session cookie](session-cookies.md) issued by your own auth service is
  simpler and has no authorization-server hop to operate.
- The client cannot securely store a client secret and cannot perform
  [PKCE](https://www.rfc-editor.org/rfc/rfc7636) — a constrained device
  with no browser and no way to receive a redirect. The device
  authorization grant (as GitHub implements for its CLI, see Real-world
  implementations) exists for exactly this case; a bare authorization code
  grant does not fit it.

## How it works

``` mermaid
sequenceDiagram
  autonumber
  actor User
  participant Client as Client app
  participant AS as Authorization server
  participant RS as Resource server
  Client->>Client: generate code_verifier, derive code_challenge (S256)
  Client->>AS: GET /authorize (client_id, redirect_uri, scope, state, code_challenge)
  AS->>User: prompt login + consent
  User-->>AS: approve
  AS-->>Client: redirect with authorization code + state
  Client->>Client: verify state matches
  Client->>AS: POST /token (code, code_verifier, redirect_uri)
  AS->>AS: verify code_verifier against stored code_challenge
  AS-->>Client: access token (+ refresh token)
  Client->>RS: request with Authorization: Bearer <access token>
  RS->>RS: validate token, check scope
  RS-->>Client: protected resource
```

## Pros and cons

- **Pro**: the client never sees or stores the resource owner's password —
  the authorization server is the only party that authenticates the user.
- **Pro**: access is scoped and revocable independently of the user's
  primary credential; a leaked access token exposes only what its `scope`
  grants, not the whole account.
- **Con**: the framework itself is deliberately underspecified. RFC 6749
  defines the message flow but leaves substantial implementation choices —
  token format, revocation, PKCE enforcement — to profiles built on top,
  which is why misconfiguration (open redirect URIs, missing state
  validation) is common in practice.
- **Con**: introduces a redirect-based flow through a browser, which adds
  failure modes (redirect URI mismatches, blocked popups, CSRF via the
  callback) that a direct password check does not have.

## Alternatives

- **[OIDC](oidc.md)** builds identity on top of this same flow when the
  requirement is authentication rather than delegated authorization.
- **[Enterprise SSO](enterprise-sso.md)** via SAML solves a similar
  federation problem for enterprise identity providers that predate OAuth.
- **A direct API key or signed request** (mutual TLS, HMAC-signed
  requests) is simpler than standing up an authorization server when there
  is no third-party user consent step to model — see the
  [module overview](index.md#when-not-to-use).

## Security considerations

- [OAuth security](../../security/oauth-security.md) — redirect URI
  validation, `state` parameter, and PKCE enforcement.
- [Session security](../../security/session-security.md) — what happens
  to the token or session on the client side after the exchange completes.
- [Refresh tokens](refresh-tokens.md) — rotation and reuse detection for
  the long-lived credential the token endpoint can also issue.

Run any new OAuth integration against the
[authentication checklist](../../checklists/authentication.md) before
shipping it.

## Implementation examples

- **Always use PKCE, even with a confidential client**: [RFC 6749](https://www.rfc-editor.org/rfc/rfc6749)
  §2.1 defines a public client as one "incapable of maintaining the
  confidentiality of their credentials... and incapable of secure client
  authentication via any other means" — exactly the case
  [RFC 7636](https://www.rfc-editor.org/rfc/rfc7636) §1 was written for:
  RFC 7636 states that "OAuth 2.0 public clients... are susceptible to
  the authorization code interception attack," in which "the attacker
  intercepts the authorization code returned from the authorization
  endpoint" and "can use it to obtain the access token." PKCE binds the
  authorization code to the client that requested it via
  `code_verifier`/`code_challenge`, defeating that interception. Generate
  the verifier with a cryptographically random value and derive the
  challenge with `S256`, not `plain`.
- **Validate `redirect_uri` with an exact string match**, not a prefix or
  pattern match, against a pre-registered allowlist — RFC 6749 §10.6
  requires the authorization server to ensure the redirection URI used to
  obtain the code "is identical to the redirection URI provided when
  exchanging the authorization code for an access token," and to
  "validate it against the registered value." A loose match is the most
  common OAuth misconfiguration.
- **Always send and verify `state`**: RFC 6749 §4.1.1 defines it as "an
  opaque value used by the client to maintain state between the request
  and callback," and in practice it is the CSRF defense for the redirect
  step — reject any callback whose `state` does not match the value the
  client generated.
- **Device flow for input-constrained clients**: for a CLI or a TV app
  that cannot receive a redirect, use the device authorization grant
  rather than trying to force an authorization-code flow onto a client
  with no browser — see GitHub's implementation below.

## Common mistakes

### Treating the access token as proof of identity

An access token only proves the bearer was granted some scope by the
authorization server; RFC 6749 defines no standard claims about who the
resource owner is. An application that logs a user in based solely on
successfully fetching a resource with the token has built authentication
on a framework that does not provide it. Use [OIDC](oidc.md)'s ID token,
which is a signed assertion of identity, when the requirement is knowing
who the user is, not merely what the client can fetch.

### Skipping PKCE because the client has a client secret

Confidential clients (a server-side web app) can hold a secret, but the
authorization code is still transmitted through the user's browser via a
redirect, where it can be intercepted by a malicious app registered for
the same custom URI scheme on a shared device, or logged by an
intermediary. RFC 7636 recommends PKCE as a defense against authorization
code interception regardless of client type. Use PKCE on every client,
public or confidential.

### Using a loose or wildcard redirect URI match

An authorization server that accepts any URI matching a prefix or pattern
lets an attacker register a lookalike redirect endpoint and receive
authorization codes intended for the real client. RFC 6749 requires exact
comparison against a registered value. Register exact, complete redirect
URIs and reject anything that does not match byte-for-byte.

## Real-world implementations

- **GitHub** documents its [device authorization
  flow](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps)
  as intended "for apps that don't have access to a web browser," listing
  headless apps such as CLI tools as the target case: the device displays
  a short code and a URL, the user enters the code at
  `github.com/login/device` on a separate browser, and the device polls
  the token endpoint until authorization completes — solving the
  no-redirect-target problem this page's When-not-to-use section flags for
  a bare authorization code grant.

## References

<!-- generated:references start -->
| Type | Source |
| --- | --- |
| RFC | [RFC 6749 — The OAuth 2.0 Authorization Framework](https://www.rfc-editor.org/rfc/rfc6749) |
| RFC | [RFC 7636 — Proof Key for Code Exchange (PKCE)](https://www.rfc-editor.org/rfc/rfc7636) |
| Vendor | [GitHub Docs — Authorizing OAuth Apps (device flow)](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps) |
<!-- generated:references end -->

<!-- generated:page-footer start -->
**Status:** reviewed · **Last reviewed:** 2026-09-07 · **Review due:** 2027-03-06
<!-- generated:page-footer end -->
