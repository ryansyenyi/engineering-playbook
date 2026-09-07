---
title: Magic link
module: authentication
status: reviewed
reviewed: 2026-09-07
tags: [Authentication, Passwordless]
sources:
  - { type: standard, name: "OWASP Authentication Cheat Sheet", url: "https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html" }
  - { type: standard, name: "OWASP Forgot Password Cheat Sheet", url: "https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html" }
  - { type: rfc, name: "RFC 6238 — TOTP: Time-Based One-Time Password Algorithm", url: "https://www.rfc-editor.org/rfc/rfc6238" }
  - { type: standard, name: "NIST SP 800-63B — Digital Identity Guidelines: Authentication and Lifecycle Management", url: "https://pages.nist.gov/800-63-3/sp800-63b.html" }
  - { type: vendor, name: "Auth0 Docs — Passwordless authentication (magic links and email OTP)", url: "https://auth0.com/docs/authenticate/passwordless" }
---

# Magic link

## Executive summary

### Purpose

A magic link authenticates a user by proving they control an email inbox:
the user submits their email address, the application generates a single-
use, short-lived, signed token, emails a link containing it, and clicking
the link exchanges the token for a session. No password is registered or
stored — the inbox itself is the credential.

### When to use

Use a magic link for low-friction consumer signup and login where the only
identifier you can rely on is an email address, where password reset is
already most of your login volume (so you are already trusting the inbox
half the time), or as the first-login step in a funnel that upgrades the
user to a [passkey](passkeys.md) immediately after, per the
[module overview](index.md#implementation-examples).

### When not to use

- The account needs a higher assurance level than "controls this inbox
  right now." [NIST SP 800-63B](https://pages.nist.gov/800-63-3/sp800-63b.html)
  is explicit that "methods that do not prove possession of a specific
  device, such as voice-over-IP (VOIP) or email, SHALL NOT be used for
  out-of-band authentication" — email cannot prove which device or person
  is reading it, only that someone with inbox access did.
- The environment runs behind a corporate email security gateway that
  prefetches links to scan them for malware. A single-use token gets
  consumed by the scanner before the real user ever clicks it; see Common
  mistakes below.
- The email address is shared (a team alias, a shared support inbox) or
  routinely forwarded. Anyone downstream of the forward gets the session
  the link would have granted.
- Login needs to work offline or without network access to the mail
  provider at the moment of login — a device-bound credential such as a
  [passkey](passkeys.md) or a [TOTP](https://www.rfc-editor.org/rfc/rfc6238)
  code does not have this dependency.

## How it works

``` mermaid
sequenceDiagram
  autonumber
  actor User
  participant App as Application
  participant Auth as Auth service
  participant Mail as Mail provider
  User->>App: POST /login (email)
  App->>Auth: issue single-use token
  Auth->>Auth: cryptographically random token, short expiry
  Auth->>Mail: send email containing link + token
  App-->>User: 200 (uniform message, no enumeration)
  User->>Mail: opens inbox, clicks link
  Mail-->>App: GET /verify?token (in user's browser)
  App->>Auth: validate token
  alt token valid and unused
    Auth->>Auth: invalidate token (single use)
    Auth-->>App: verified
    App-->>User: 200 + session (see session-cookies.md)
  else token invalid, expired, or already used
    Auth-->>App: rejected
    App-->>User: 401 (request a new link)
  end
```

## Pros and cons

- **Pro**: no password to register, hash, store, or reset — removes the
  entire password-storage attack surface described on the
  [email/password page](email-password.md).
- **Pro**: recovery and login are the same flow, which removes a whole
  category of "forgot password" UX and the account-enumeration risk that
  flow usually carries.
- **Con**: security is bounded by inbox security. A compromised mailbox
  (weak email-account password, no MFA on the mail provider) is a
  compromised application account, with no independent factor in between.
- **Con**: email delivery is not instant or guaranteed — spam filtering,
  greylisting, and provider outages all show up as login failures the
  application cannot fully control.
- **Con**: single-use tokens delivered by link are vulnerable to automated
  consumption by anything that follows the link before the user does —
  see Common mistakes.

## Alternatives

- **[TOTP](https://www.rfc-editor.org/rfc/rfc6238)** generates a short-lived
  code from a shared secret already provisioned on the user's device,
  rather than depending on a message being delivered over email at login
  time. RFC 6238 frames this as replacing a static, indefinitely valid
  secret with "short-lived OTP values, which are desirable for enhanced
  security" — the same time-boxing goal a magic link's token expiry serves,
  but without a delivery channel in the critical path and without the
  device-possession gap NIST SP 800-63B flags for email.
- **[Passkeys](passkeys.md)** remove the delivery channel and the shared
  secret entirely, binding the credential to a specific authenticator.
- **[Email/password](email-password.md)** trades the inbox dependency for
  a stored-secret dependency — appropriate when password-storage hygiene
  is easier to guarantee than inbox security across your user base.

## Security considerations

- [Rate limiting](../../security/rate-limiting.md) — throttle link
  requests per email address and per IP to stop mailbox-flooding and
  token-guessing.
- [Session security](../../security/session-security.md) — what the
  exchanged token becomes once the user is verified.
- [MFA](../../security/mfa.md) — consider requiring a second factor for
  sensitive actions even after a magic-link login, since the login itself
  only proves inbox control.

Run the flow against the
[authentication checklist](../../checklists/authentication.md), in
particular the uniform-response requirement shared with
[email/password](email-password.md#common-mistakes).

## Implementation examples

- **Token generation**: per the
  [OWASP Forgot Password Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html)
  (the closest OWASP guidance to magic-link mechanics, since a login link
  and a password-reset link are the same primitive), generate the token
  "randomly generated using a cryptographically safe algorithm" and
  "sufficiently long to protect against brute-force attacks," make it
  "single use and expire after an appropriate period," and invalidate it
  immediately once used.
- **Transport hygiene**: serve the verification link over HTTPS only, and
  set a `noreferrer` referrer policy on the landing page so the token does
  not leak to a third party through the `Referer` header if that page
  links elsewhere.
- **Defeating prefetch scanners**: do not consume the token on the initial
  `GET`. Land on an intermediate page that requires an explicit user
  action (a "Confirm sign-in" button that issues the consuming `POST`), or
  detect known scanner user agents and return `200` without consuming the
  token — automated prefetching cannot complete a human click or reliably
  fake every scanner signature at once.
- **Uniform response**: respond identically to `POST /login` whether or
  not the email address has an account, exactly as
  [email/password](email-password.md) does for login failures, so the
  endpoint cannot be used to enumerate registered addresses.

## Common mistakes

### Validating the token on the link's `GET` request

Corporate email security gateways (and some client link-preview features)
fetch every URL in an incoming email to scan it for malware before the
recipient ever opens the message. If the verification endpoint consumes
the token on `GET`, the scanner consumes it first, and the legitimate user
clicks a link that is already dead. This is a direct consequence of the
gap NIST SP 800-63B identifies — email as a channel proves nothing about
which specific client is acting on it, scanner or human. Move consumption
to an explicit user action (a confirmation button triggering a `POST`), or
allow a bounded number of uses within the expiry window instead of exactly
one.

### Treating a forwarded or shared-inbox email as proof of identity

A magic link grants access to whoever clicks it, and nothing in the
mechanism distinguishes the intended recipient from anyone they forwarded
the email to, or anyone else with access to a shared support alias. OWASP's
uniform-response guidance addresses enumeration, not this: it is a property
of the credential model itself. Treat magic-link login as proof of inbox
access, not proof of the individual's identity, and require a stronger
factor before authorizing high-value actions.

### Reusing the login token as a long-lived session identifier

Per the OWASP Forgot Password Cheat Sheet, the token must be "invalidated
after they have been used." A magic-link token that is only checked for
expiry, and not marked used, can be replayed by anyone who intercepted the
original email (a shared mailbox, a compromised mail server, a logged
copy) for as long as it remains unexpired. Invalidate it on first
successful use and issue a separate session credential — see
[session cookies](session-cookies.md) — for everything that follows.

## Real-world implementations

- **Auth0** ships passwordless email authentication as two distinct
  methods — the magic link this page describes, and an email one-time
  code typed back into the app — and
  [restricts the magic-link variant to its older "Classic Login"
  experience](https://auth0.com/docs/authenticate/passwordless) rather
  than its current default flow, treating the typed-code variant as the
  one to reach for by default. That split matches this page's Common
  mistakes: a clickable link is exposed to automated consumption in a way
  a code the user must read and type is not.

## References

<!-- generated:references start -->
| Type | Source |
| --- | --- |
| Standard | [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html) |
| Standard | [OWASP Forgot Password Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html) |
| RFC | [RFC 6238 — TOTP: Time-Based One-Time Password Algorithm](https://www.rfc-editor.org/rfc/rfc6238) |
| Standard | [NIST SP 800-63B — Digital Identity Guidelines: Authentication and Lifecycle Management](https://pages.nist.gov/800-63-3/sp800-63b.html) |
| Vendor | [Auth0 Docs — Passwordless authentication (magic links and email OTP)](https://auth0.com/docs/authenticate/passwordless) |
<!-- generated:references end -->

<!-- generated:page-footer start -->
**Status:** reviewed · **Last reviewed:** 2026-09-07 · **Review due:** 2027-03-06
<!-- generated:page-footer end -->
