---
title: Authentication
module: authentication
status: reviewed
reviewed: 2026-09-07
tags: [Authentication, Security]
sources:
  - { type: standard, name: "OWASP Authentication Cheat Sheet", url: "https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html" }
  - { type: rfc, name: "RFC 6749 — OAuth 2.0", url: "https://www.rfc-editor.org/rfc/rfc6749" }
  - { type: rfc, name: "RFC 9106 — Argon2", url: "https://www.rfc-editor.org/rfc/rfc9106" }
---

# Authentication

## Executive summary

### Purpose

This module covers how an application establishes and maintains a verified
identity for a request: registering an identity, verifying it at login,
issuing and rotating credentials, and closing the identity out at logout. It
links out to ten concrete mechanisms — [email/password](email-password.md),
[magic links](magic-link.md), [passkeys](passkeys.md),
[social login](social-login.md), [enterprise SSO](enterprise-sso.md),
[OIDC](oidc.md), [OAuth 2.0](oauth2.md), [JWT](jwt.md),
[session cookies](session-cookies.md), and
[refresh tokens](refresh-tokens.md) — plus the two decisions
([password hashing](../../matrices/password-hashing.md),
[JWT vs session cookies](../../matrices/jwt-vs-session-cookies.md)) that
most implementations have to make early, and the
[authentication checklist](../../checklists/authentication.md) that turns
this page into a launch gate.

### When to use

Reach for this module whenever an application has more than one user and
needs to know which one is making a request: multi-user SaaS products,
anything with per-account data, anything with an audit-log requirement,
anything gated by a subscription or a role.

### When not to use

Do not build a custom authentication stack when:

- A managed identity provider already satisfies the requirement.
  [OAuth 2.0](oauth2.md) ([RFC 6749](https://www.rfc-editor.org/rfc/rfc6749))
  and [OIDC](oidc.md) exist so that most applications can delegate
  authentication instead of re-implementing it; every hand-rolled password
  flow is one more place credential handling can go wrong.
- The system is machine-to-machine only. Service-to-service calls are
  better served by mutual TLS or short-lived signed credentials than by a
  user-facing login flow.
- There is no notion of a returning user. A stateless, anonymous public API
  has nothing for this module to authenticate.

## Architecture overview

A login request never touches the stored credential directly — it is
checked against a hash, and only a session (or token) leaves the auth
service. The sequence below is the shape shared by every mechanism in this
module:

``` mermaid
sequenceDiagram
  autonumber
  actor User
  participant App as Application
  participant Auth as Auth service
  participant DB as User store
  User->>App: POST /login (email, password)
  App->>Auth: verify(email, password)
  Auth->>DB: fetch password hash
  DB-->>Auth: argon2id hash
  Auth->>Auth: verify hash (constant time)
  alt credentials valid
    Auth->>Auth: create session
    Auth-->>App: session id
    App-->>User: 200 + Set-Cookie (HttpOnly, Secure, SameSite=Lax)
  else credentials invalid
    Auth-->>App: failure
    App-->>User: 401 (uniform message)
  end
```

## Flow diagram

Two flows sit alongside login and deserve their own diagrams, because each
has a failure mode that is easy to get wrong: resetting a forgotten password
without leaking which addresses have accounts, and rotating a refresh token
without opening a replay window.

``` mermaid
sequenceDiagram
  autonumber
  actor User
  participant App as Application
  participant Auth as Auth service
  participant Mail as Mail service
  User->>App: POST /forgot (email)
  App->>Auth: issue reset token
  Auth->>Auth: single-use token, short expiry
  Auth->>Mail: send reset link
  App-->>User: 200 (uniform message, always)
  User->>App: GET /reset?token
  App->>Auth: validate token
  Auth-->>App: valid
  User->>App: POST /reset (new password)
  App->>Auth: rehash + invalidate all sessions
  Auth-->>App: done
  App-->>User: 200 + new session
```

``` mermaid
sequenceDiagram
  autonumber
  participant Client
  participant Auth as Auth service
  participant Store as Token store
  Client->>Auth: POST /token (refresh token)
  Auth->>Store: look up token family
  alt token already used
    Auth->>Store: revoke entire family
    Auth-->>Client: 401 (reuse detected)
  else token valid
    Auth->>Store: rotate — mark used, issue successor
    Auth-->>Client: new access + refresh token
  end
```

## Functional requirements

- Users can register with email and password
- Users can log in and log out
- Users can reset a forgotten password
- Users can change a known password
- Users can enable and disable MFA
- Users can see and revoke active sessions

## Non-functional requirements

- 99.9% availability for the login path
- Login response under 300 ms at the 95th percentile
- Password verification under 500 ms
- Idle session timeout of 8 hours

## Pros and cons

**Owning authentication in-house**

- Pro: full control over login UX, credential lifecycle, and session model
  — not throttled by a third party's rate limits or pricing tiers.
- Pro: the login path's availability target above is yours to meet; it does
  not depend on an external vendor's uptime.
- Con: every mechanism this module lists —
  [passkeys](passkeys.md), [social login](social-login.md),
  [enterprise SSO](enterprise-sso.md) — is a maintenance surface a managed
  identity provider would otherwise absorb.
- Con: a credential-storage mistake is your incident, not a vendor's; see
  [Common mistakes](#common-mistakes) below.

**Password-based vs passwordless**

- Password-based ([email/password](email-password.md)) needs no client
  hardware support, but pushes the security work into hashing (see the
  [password hashing matrix](../../matrices/password-hashing.md)) and
  breach-list checking.
- Passwordless ([magic links](magic-link.md), [passkeys](passkeys.md))
  removes the stored-secret attack surface, but trades it for email or
  device availability as a new dependency.

## Alternatives

- **Delegate to an external identity provider** via [OAuth 2.0](oauth2.md)
  ([RFC 6749](https://www.rfc-editor.org/rfc/rfc6749)) and [OIDC](oidc.md)
  instead of storing credentials at all — the right default when
  [social login](social-login.md) or [enterprise SSO](enterprise-sso.md)
  already covers the target users.
- **Token model**: stateless [JWTs](jwt.md) versus stateful
  [session cookies](session-cookies.md); see the
  [JWT vs session cookies matrix](../../matrices/jwt-vs-session-cookies.md)
  for the tradeoff on revocation.
- **Long-lived access**: [refresh tokens](refresh-tokens.md) with rotation
  instead of a single long-lived access token, to bound the damage of a
  leaked credential.

## Security considerations

Security guidance for this module lives entirely in
[docs/security/](../../security/index.md); this page links out to it rather
than duplicating it inline:

- [Password storage](../../security/password-storage.md) — hashing
  algorithm choice and parameters.
- [Session security](../../security/session-security.md) — cookie flags,
  fixation, rotation.
- [MFA](../../security/mfa.md) — enrollment and recovery.
- [OAuth security](../../security/oauth-security.md) — redirect URI
  validation, state and PKCE.
- [Rate limiting](../../security/rate-limiting.md) — login and reset
  endpoints.
- [SSO](../../security/sso.md) — enterprise identity federation.

Before shipping any authentication surface, run it against the
[authentication checklist](../../checklists/authentication.md).

## Implementation examples

- **New consumer product with only email addresses**: start with
  [email/password](email-password.md) hashed with Argon2id per
  [ADR 0001](../../decisions/0001-argon2id-for-password-hashing.md), add
  [MFA](../../security/mfa.md) as opt-in, and issue
  [session cookies](session-cookies.md) rather than JWTs since the app is
  browser-facing.
- **B2B SaaS selling to companies with an identity team**: put
  [enterprise SSO](enterprise-sso.md) via [OIDC](oidc.md) in front of the
  same session model, and keep email/password as the fallback for accounts
  without a configured identity provider.
- **Mobile app calling a backend API**: use [OAuth 2.0](oauth2.md) with
  [refresh token](refresh-tokens.md) rotation rather than a long-lived
  access token, since a stolen device is the realistic threat model.
- **Passwordless signup funnel**: [magic links](magic-link.md) for first
  login, [passkeys](passkeys.md) offered immediately after as the durable
  credential, since a magic link is only as secure as the inbox behind it.

## Common mistakes

- **Mistake**: storing passwords with a fast, general-purpose hash, or a
  legacy PBKDF2 configuration, instead of a memory-hard one. This is
  dangerous because an attacker with a stolen database can trade cheap GPU
  or ASIC parallelism for the memory cost the algorithm should have
  demanded, and crack a large share of a leaked database offline. Safer
  alternative: hash with Argon2id per the
  [password hashing matrix](../../matrices/password-hashing.md) and
  [ADR 0001](../../decisions/0001-argon2id-for-password-hashing.md).
- **Mistake**: storing a JWT in `localStorage` for a browser app. This is
  dangerous because any script-injection vulnerability can read
  `localStorage` and exfiltrate the token, and a JWT cannot be revoked
  before it expires. Safer alternative: use an `HttpOnly` session cookie
  for browser-facing apps — see the
  [JWT vs session cookies matrix](../../matrices/jwt-vs-session-cookies.md).
- **Mistake**: returning a different error for "no such account" than for
  "wrong password." This is dangerous because it lets an attacker enumerate
  which email addresses have accounts before running credential stuffing
  against them. Safer alternative: return one uniform failure message and
  keep the distinction server-side only, per the
  [authentication checklist](../../checklists/authentication.md).
- **Mistake**: treating a refresh token as reusable until it expires. This
  is dangerous because a token captured once — a log leak, an intercepted
  request — grants an attacker indefinite renewed access alongside the
  legitimate user, undetected. Safer alternative: rotate on every use and
  revoke the entire token family on reuse detection, as in the refresh
  token flow diagram above.

## Real-world implementations

- **GitHub** issues personal access tokens as a bearer-credential
  alternative to session cookies for API and `git` access, and uses an
  out-of-band device verification flow — entering a code shown by a CLI or
  TV app into a browser session — for clients that cannot host an OAuth
  redirect, the same pattern this module's [OAuth 2.0](oauth2.md) page
  covers.
- **Google** layers risk-based signals — new device, new location,
  improbable travel — on top of password verification before deciding
  whether to challenge with additional factors, and has pushed passkeys
  toward being the default credential ahead of passwords, the direction
  the [passkeys](passkeys.md) page describes.
- **Microsoft Entra** evaluates conditional access policies — device
  compliance, network location, sign-in risk — after primary authentication
  and before a token is issued, which is the enterprise extension of the
  [enterprise SSO](enterprise-sso.md) and [OIDC](oidc.md) flows this module
  documents.

## References

<!-- generated:references start -->
| Type | Source |
| --- | --- |
| Standard | [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html) |
| RFC | [RFC 6749 — OAuth 2.0](https://www.rfc-editor.org/rfc/rfc6749) |
| RFC | [RFC 9106 — Argon2](https://www.rfc-editor.org/rfc/rfc9106) |
<!-- generated:references end -->

<!-- generated:page-footer start -->
**Status:** reviewed · **Last reviewed:** 2026-09-07 · **Review due:** 2027-03-06
<!-- generated:page-footer end -->
