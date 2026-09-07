---
title: Social login
module: authentication
status: reviewed
reviewed: 2026-09-07
tags: [Authentication, OAuth]
sources:
  - { type: rfc, name: "RFC 6749 — The OAuth 2.0 Authorization Framework", url: "https://www.rfc-editor.org/rfc/rfc6749" }
  - { type: rfc, name: "RFC 6819 — OAuth 2.0 Threat Model and Security Considerations", url: "https://www.rfc-editor.org/rfc/rfc6819" }
  - { type: vendor, name: "Google Account Help — Suspicious sign-in prevented", url: "https://support.google.com/accounts/answer/6063333" }
---

# Social login

## Executive summary

### Purpose

Social login delegates authentication to a consumer identity provider the
user already has an account with (Google, GitHub, and similar) using
OAuth 2.0 — often layered with OpenID Connect on top, covered separately
on the [OIDC page](oidc.md). The application redirects the user to the
provider, the provider authenticates them and asks for consent, and the
application receives an authorization code it exchanges for a token
proving the provider granted access, per the
[OAuth 2.0](oauth2.md) flow.

### When to use

Use it when your users already hold accounts with a small number of
identity providers, when you want to skip building password storage and
reset flows entirely, or as a low-friction option offered alongside
[email/password](email-password.md) rather than as the only login method
— see the [authentication module overview](index.md) for how the
mechanisms in this module typically combine.

### When not to use

- The provider's account model does not match your trust requirements.
  RFC 6749 defines OAuth 2.0 as "an authorization framework" for a client
  to obtain access to a resource "on behalf of the resource owner" — it
  does not define an identity or login ceremony at all. RFC 6819 goes
  further and warns that "clients should use an appropriate protocol,
  such as OpenID or SAML to implement user login" rather than bare OAuth
  — see Common mistakes below.
- The audience is an enterprise buyer with its own identity provider.
  [Enterprise SSO](enterprise-sso.md) integrates with their directory
  directly; social login authenticates against a personal, not
  organizational, identity.
- You cannot tolerate depending on the provider's uptime and policies for
  every login. An outage or a suspended developer account at the provider
  becomes an outage for your product.

## How it works

``` mermaid
sequenceDiagram
  autonumber
  actor User
  participant App as Client application
  participant Browser
  participant IdP as Identity provider (authorization server)
  User->>App: click "Sign in with Provider"
  App->>Browser: redirect to IdP with client_id, redirect_uri, state
  Browser->>IdP: authorization request
  IdP->>User: authenticate + consent screen
  User->>IdP: approve
  IdP->>Browser: redirect to redirect_uri with authorization code + state
  Browser->>App: authorization code + state
  App->>App: verify state matches (CSRF check)
  App->>IdP: exchange code for token (client authenticates itself)
  IdP-->>App: access token (+ ID token if OIDC)
  App->>IdP: fetch profile (email, name)
  IdP-->>App: profile claims
  App->>App: check email_verified before trusting email
  App-->>User: session (see session-cookies.md)
```

## Pros and cons

- **Pro**: no password to store, hash, or reset for accounts created this
  way — the identity provider owns that surface entirely.
- **Pro**: lower signup friction; the user reuses an existing session with
  the provider instead of creating a new credential.
- **Con**: RFC 6749 scopes OAuth 2.0 to authorization, not authentication,
  so anything built on it to establish "who is this user" is layering a
  login ceremony on top of a protocol that was not designed to provide
  one — the exact gap RFC 6819 calls out.
- **Con**: RFC 6819 documents concrete attacks against OAuth used this way
  — "Code Substitution" and "Token Substitution," where a malicious client
  or attacker gets a code or token issued to one identity accepted for a
  different one — that a naive implementation is exposed to.
- **Con**: account linking by email address inherits whatever verification
  guarantees (or lack of them) the provider's profile data carries.

## Alternatives

- **[OIDC](oidc.md)** is the protocol RFC 6819 points toward — an
  identity layer built on top of OAuth 2.0 specifically to provide a
  verifiable, signed identity assertion (an ID token), rather than relying
  on a resource-server profile endpoint the way bare OAuth-as-login does.
- **[Enterprise SSO](enterprise-sso.md)** for organizational identity
  instead of a personal consumer account.
- **[Email/password](email-password.md)** or **[passkeys](passkeys.md)**
  when you want to own the credential and not depend on a third party's
  availability or account policies at all.

## Security considerations

- [OAuth security](../../security/oauth-security.md) — redirect URI
  validation, `state` parameter, and PKCE, all directly relevant to the
  flow above.
- [Session security](../../security/session-security.md) — what the
  application issues after the provider round trip completes.
- [Rate limiting](../../security/rate-limiting.md) — the token-exchange
  and profile-fetch endpoints are still endpoints an attacker can probe.

Validate every new provider integration against the
[authentication checklist](../../checklists/authentication.md) and RFC
6819's threat list before launch.

## Implementation examples

- **`state` parameter**: per RFC 6819, the `state` parameter exists to
  prevent cross-site request forgery against the callback — generate it
  unpredictably, bind it to the user's browser session, and reject any
  callback whose `state` does not match.
- **Redirect URI validation**: RFC 6819 identifies the open redirector as
  a way for an attacker to intercept an authorization code or token in
  transit, and its countermeasure is registering complete, exact redirect
  URIs with the provider rather than a pattern or partial match — reject
  any authorization response addressed to a URI that is not an exact,
  pre-registered match.
- **Authorization code exchange**: per RFC 6749, exchange the code at the
  token endpoint with the client authenticating itself to the
  authorization server, server-side, never in the browser — the code
  alone should never be treated as sufficient to grant a session.
- **Profile claim checks**: before trusting an email address returned by
  the provider's profile endpoint, verify it is marked verified by that
  provider. Do not create or link an account to an email the provider has
  not itself confirmed ownership of. See Common mistakes.

## Common mistakes

### Trusting a provider's `email` claim without checking it is verified

An OAuth or OIDC identity provider can return an `email` field without
guaranteeing the underlying address was ever confirmed to belong to that
account — providers expose a separate verified flag precisely because the
two are not the same fact. An application that links or creates accounts
on the raw `email` value, without checking that flag, lets an attacker who
registers with a victim's address (leaving it unverified with the
provider) get logged into the victim's account on your service through
social login. This is the same class of flaw
[Google's own account-protection documentation](https://support.google.com/accounts/answer/6063333)
exists to catch at the provider layer — unrecognized or unverified sign-in
activity — and RFC 6819's "Code Substitution" and "Token Substitution"
threats describe the general shape of trusting an identity assertion that
was not validated as belonging to the party presenting it. Check the
verified flag before using an email claim for account linking, and require
a confirmation step for any address the provider has not itself verified.

### Using bare OAuth 2.0 as if it were a login protocol

RFC 6749 defines OAuth 2.0 to let "a client to obtain access to a
resource" — nothing in that scope is a signed statement of identity. RFC
6819 is explicit about the consequence: "Clients should use an
appropriate protocol, such as OpenID or SAML to implement user login."
An application that treats "I obtained an access token that can read this
provider's `/me` endpoint" as equivalent to "I have proven who this user
is" is relying on a guarantee the protocol never made, and inherits the
Code Substitution and Token Substitution threats RFC 6819 documents for
exactly this misuse. Use [OIDC](oidc.md)'s signed ID token as the identity
assertion, and treat the OAuth access token as authorization to call an
API — nothing more.

### Skipping `state` validation on the callback

Without a `state` value tied to the user's session, the callback endpoint
cannot tell a legitimate authorization response from one an attacker
engineered by tricking the victim into completing a login the attacker
initiated (a login CSRF). RFC 6819 calls this out directly as the purpose
of the parameter. Generate an unpredictable `state`, store it against the
session that initiated the request, and reject the callback outright if it
does not match.

## Real-world implementations

- **Google** documents that it actively
  [blocks or flags sign-in attempts it does not
  recognize](https://support.google.com/accounts/answer/6063333) — for
  example a sign-in "from a different location or device than normal" —
  as a provider-side control that social-login consumers benefit from
  without implementing it themselves, but which does not remove the
  relying application's own obligation to validate `state`, verify email
  claims, and follow RFC 6819's threat mitigations on its own side of the
  flow.

## References

<!-- generated:references start -->
| Type | Source |
| --- | --- |
| RFC | [RFC 6749 — The OAuth 2.0 Authorization Framework](https://www.rfc-editor.org/rfc/rfc6749) |
| RFC | [RFC 6819 — OAuth 2.0 Threat Model and Security Considerations](https://www.rfc-editor.org/rfc/rfc6819) |
| Vendor | [Google Account Help — Suspicious sign-in prevented](https://support.google.com/accounts/answer/6063333) |
<!-- generated:references end -->

<!-- generated:page-footer start -->
**Status:** reviewed · **Last reviewed:** 2026-09-07 · **Review due:** 2027-03-06
<!-- generated:page-footer end -->
