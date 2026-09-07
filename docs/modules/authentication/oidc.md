---
title: OIDC
module: authentication
status: reviewed
reviewed: 2026-09-07
tags: [Authentication, OAuth, SSO]
sources:
  - { type: standard, name: "OpenID Connect Core 1.0", url: "https://openid.net/specs/openid-connect-core-1_0.html" }
  - { type: rfc, name: "RFC 6749 — The OAuth 2.0 Authorization Framework", url: "https://www.rfc-editor.org/rfc/rfc6749" }
  - { type: vendor, name: "Microsoft Learn — Microsoft Entra Conditional Access overview", url: "https://learn.microsoft.com/en-us/entra/identity/conditional-access/overview" }
---

# OIDC

## Executive summary

### Purpose

OpenID Connect (OIDC) is an identity layer built on top of
[OAuth 2.0](oauth2.md), one of the ten mechanisms the
[module overview](index.md#purpose) lists for establishing a verified
identity. OpenID Connect Core 1.0's Abstract describes it as
enabling clients "to verify the identity of the End-User based on the
authentication performed by an Authorization Server, as well as to obtain
basic profile information about the End-User." It reuses OAuth 2.0's
authorization code flow from [RFC 6749](https://www.rfc-editor.org/rfc/rfc6749)
but adds a signed **ID token** — a JWT asserting who the user is —
alongside the access token OAuth 2.0 already returns. Where OAuth 2.0
answers what a client can *do*, OIDC answers who the user *is*.

### When to use

Use OIDC whenever the actual requirement is authenticating a user against
an external identity provider — [social login](social-login.md) against
Google or a similar consumer provider, or [enterprise SSO](enterprise-sso.md)
against an identity platform that offers an OIDC endpoint (many do, as an
alternative to SAML). If you are building a check for what a token can
*access* without ever needing to know who the user is, you likely want
bare [OAuth 2.0](oauth2.md) instead.

### When not to use

- The identity provider only exposes SAML, not OIDC — enterprise identity
  platforms built before OIDC's adoption sometimes only support the SAML
  federation model; see [enterprise SSO](enterprise-sso.md).
- There is no external identity provider at all and the application owns
  the credential itself. Plain [email/password](email-password.md) or
  [passkeys](passkeys.md) issuing your own [session cookie](session-cookies.md)
  is simpler than standing up or federating with an OIDC provider for a
  single first-party user base.
- The integration only needs delegated resource access with no identity
  requirement — use [OAuth 2.0](oauth2.md) alone and skip the ID token
  entirely.

## How it works

``` mermaid
sequenceDiagram
  autonumber
  actor User
  participant Client as Relying party (Client)
  participant OP as OpenID Provider
  participant JWKS as OP JWKS endpoint
  Client->>OP: GET /authorize (scope=openid profile email, state, nonce, code_challenge)
  OP->>User: prompt login + consent
  User-->>OP: approve
  OP-->>Client: redirect with authorization code + state
  Client->>OP: POST /token (code, code_verifier)
  OP-->>Client: ID token (JWT) + access token
  Client->>Client: verify ID token signature, iss, aud, exp, nonce
  Client->>JWKS: fetch signing keys (cached)
  JWKS-->>Client: public keys
  Client->>OP: GET /userinfo (Authorization: Bearer access token)
  OP-->>Client: profile claims
  Client-->>User: authenticated session (see session-cookies.md)
```

## Pros and cons

- **Pro**: reuses OAuth 2.0's well-understood redirect and token-exchange
  machinery rather than inventing a new protocol, so infrastructure built
  for OAuth 2.0 (PKCE, token endpoints) carries over directly.
- **Pro**: the ID token is a signed, self-contained assertion the client
  can verify offline against the provider's published keys, without a
  round trip for every check.
- **Con**: inherits every OAuth 2.0 redirect-flow risk — `state`/`nonce`
  handling, redirect URI validation — described on the
  [OAuth 2.0 page](oauth2.md#common-mistakes); getting OIDC right requires
  getting OAuth 2.0 right first.
- **Con**: the ID token is a JWT, so it inherits the JWT lifecycle and
  storage tradeoffs documented on the [JWT page](jwt.md) — it must be
  verified, not merely decoded, and it is not itself a revocable session.

## Alternatives

- **[OAuth 2.0](oauth2.md)** alone, when only delegated resource access is
  needed and no identity assertion is required.
- **[Enterprise SSO](enterprise-sso.md) via SAML** for identity providers
  that only speak SAML rather than OIDC.
- **[Email/password](email-password.md)** or **[passkeys](passkeys.md)**
  as first-party credentials when there is no external identity provider
  to federate with at all.

## Security considerations

- [OAuth security](../../security/oauth-security.md) — the redirect,
  `state`, and PKCE requirements OIDC inherits from OAuth 2.0.
- [SSO](../../security/sso.md) — federation-specific hardening shared with
  [enterprise SSO](enterprise-sso.md).
- [Session security](../../security/session-security.md) — what the
  verified ID token becomes once exchanged for an application session.

Validate any new OIDC integration against the
[authentication checklist](../../checklists/authentication.md).

## Implementation examples

- **Always request and verify `nonce`**: OpenID Connect Core 1.0 §3.1.2.1
  defines `nonce` as a "String value used to associate a Client session
  with an ID Token, and to mitigate replay attacks." Generate it per
  authentication request, include it in the authorization request, and
  confirm the value returned inside the ID token matches before accepting
  the token.
- **Verify the ID token fully before trusting it**: per OpenID Connect
  Core 1.0, the client must validate the signature against the issuer's
  published keys, confirm `iss` matches the expected provider, confirm the
  client's own `client_id` is present in `aud`, and confirm the token has
  not expired (`exp`). A token that merely decodes without error has not
  been verified.
- **Use the `openid` scope plus only the claims you need**: request
  `profile` or `email` scopes individually rather than requesting every
  available claim, minimizing what the relying party receives and stores
  about the user.
- **Cache the provider's JWKS, but respect key rotation**: fetch signing
  keys from the OpenID Provider's published JWKS endpoint and cache them,
  but re-fetch on a signature-verification failure with an unrecognized
  `kid` before rejecting the token outright, since providers rotate keys.

## Common mistakes

### Accepting an ID token without verifying its signature

An ID token is a JWT, and a JWT payload can be decoded by anyone without
any cryptographic check — decoding is not verification. OpenID Connect
Core 1.0 requires validating the signature against the issuer's keys
before trusting any claim inside it. An attacker who can present an
unverified, self-signed token can claim to be any user. Always verify the
signature, `iss`, and `aud` before reading claims — see the
[JWT common mistakes](jwt.md#common-mistakes) for the same failure mode in
a broader context.

### Skipping `nonce` validation

Without a `nonce` bound to the specific authentication request, a captured
ID token from one session can potentially be replayed into another. OpenID
Connect Core 1.0 §3.1.2.1 defines `nonce` specifically "to mitigate replay
attacks." Generate a fresh `nonce` per login attempt, store it
server-side or in a signed cookie, and reject any ID token whose `nonce`
claim does not match.

### Conflating the ID token with a session

The ID token proves who authenticated at a point in time; it is not
designed to be the ongoing session credential and, like any JWT, cannot be
revoked before it expires. Exchange it once for an application-managed
[session cookie](session-cookies.md) or a short-lived access token with
[refresh token](refresh-tokens.md) rotation, rather than treating the ID
token itself as long-lived proof of an active session.

## Real-world implementations

- **Microsoft Entra** exposes OIDC endpoints alongside SAML for enterprise
  federation, and layers [Conditional
  Access](https://learn.microsoft.com/en-us/entra/identity/conditional-access/overview)
  policies "enforced after first-factor authentication is completed" on
  top of the OIDC sign-in — the same post-authentication risk evaluation
  the [enterprise SSO](enterprise-sso.md) page describes for SAML
  federation.

## References

<!-- generated:references start -->
| Type | Source |
| --- | --- |
| Standard | [OpenID Connect Core 1.0](https://openid.net/specs/openid-connect-core-1_0.html) |
| RFC | [RFC 6749 — The OAuth 2.0 Authorization Framework](https://www.rfc-editor.org/rfc/rfc6749) |
| Vendor | [Microsoft Learn — Microsoft Entra Conditional Access overview](https://learn.microsoft.com/en-us/entra/identity/conditional-access/overview) |
<!-- generated:references end -->

<!-- generated:page-footer start -->
**Status:** reviewed · **Last reviewed:** 2026-09-07 · **Review due:** 2027-03-06
<!-- generated:page-footer end -->
