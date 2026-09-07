---
title: Email and password
module: authentication
status: reviewed
reviewed: 2026-09-07
tags: [Authentication, Password Storage]
sources:
  - { type: standard, name: "OWASP Authentication Cheat Sheet", url: "https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html" }
  - { type: standard, name: "OWASP Password Storage Cheat Sheet", url: "https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html" }
  - { type: vendor, name: "Have I Been Pwned — Pwned Passwords API (k-anonymity model)", url: "https://haveibeenpwned.com/API/v3#PwnedPasswords" }
---

# Email and password

## Executive summary

### Purpose

Email and password is the default authentication mechanism: a user
registers an email address and a secret, the application stores a hash of
that secret, and every later login recomputes and compares a hash rather
than the secret itself. Everything this module calls "the credential" lives
in one place — the password store — and every other page in this
[authentication module](index.md) (sessions, refresh tokens, MFA) builds
on top of the session it produces.

### When to use

Use it when there is no existing identity provider covering your users
(no shared enterprise directory, no social account the audience already
trusts), when the product needs to work for users who may not have a phone
number or a second device, or as the fallback path underneath
[social login](social-login.md) or [enterprise SSO](enterprise-sso.md) for
accounts that were not provisioned through either.

### When not to use

- The audience already authenticates somewhere you can delegate to — a
  company directory ([enterprise SSO](enterprise-sso.md)) or a consumer
  identity provider ([social login](social-login.md)). Every password you
  store is a breach liability the delegate would have carried instead.
- The product can require a hardware-backed credential. [Passkeys](passkeys.md)
  remove the shared-secret attack surface (credential stuffing, breach
  reuse) that this page's entire threat model exists to manage.
- The login is machine-to-machine. There is no human to type a password;
  use a signed credential or mutual TLS instead.

## How it works

``` mermaid
sequenceDiagram
  autonumber
  actor User
  participant App as Application
  participant Auth as Auth service
  participant DB as Password store
  participant HIBP as Breach-check service
  User->>App: POST /register (email, password)
  App->>HIBP: k-anonymity range query (first 5 hash chars)
  HIBP-->>App: matching suffixes + counts
  App->>App: reject if password suffix found
  App->>Auth: hash password (Argon2id)
  Auth->>DB: store hash + parameters
  User->>App: POST /login (email, password)
  App->>Auth: verify(email, password)
  Auth->>DB: fetch hash + parameters
  Auth->>Auth: recompute hash, constant-time compare
  alt match
    Auth-->>App: verified
    App-->>User: 200 + session (see session-cookies.md)
  else no match
    Auth-->>App: rejected
    App-->>User: 401 (uniform message, no enumeration)
  end
```

## Pros and cons

- **Pro**: needs no client hardware capability and no dependency on a
  third-party identity provider being reachable at login time.
- **Pro**: universally understood by users — no enrollment ceremony beyond
  typing a password.
- **Con**: the entire security burden sits on how the password is stored.
  OWASP's Password Storage Cheat Sheet exists because the naive
  implementation (a fast general-purpose hash, or none) is catastrophic once
  the database leaks.
- **Con**: passwords are reused across sites, so a breach anywhere becomes
  a credential-stuffing attempt everywhere; the breach-check step above
  exists specifically to catch this at registration and change time.
- **Con**: every "forgot password" flow is an additional attack surface
  (account-enumeration risk, token-guessing risk) that passwordless
  mechanisms such as [passkeys](passkeys.md) do not need.

## Alternatives

- **[Magic link](magic-link.md)** — removes the stored-secret entirely,
  trading it for email-inbox availability as the new trust anchor.
- **[Passkeys](passkeys.md)** — removes the shared-secret attack surface
  altogether via public-key cryptography bound to the origin.
- **[Social login](social-login.md) or [enterprise SSO](enterprise-sso.md)**
  — delegates storage and verification to a provider that already
  specializes in it.

See the [password hashing matrix](../../matrices/password-hashing.md) and
[ADR 0001](../../decisions/0001-argon2id-for-password-hashing.md) for how
this playbook chose Argon2id specifically.

## Security considerations

This page states the mechanism; the hardening detail lives in
[docs/security/](../../security/index.md):

- [Password storage](../../security/password-storage.md) — hashing
  algorithm and parameter choice.
- [Session security](../../security/session-security.md) — what a
  successful verification hands back to the user.
- [Rate limiting](../../security/rate-limiting.md) — throttling login and
  password-reset endpoints against guessing and enumeration.
- [MFA](../../security/mfa.md) — the second factor that limits the blast
  radius of a leaked or guessed password.

Run every new login surface against the
[authentication checklist](../../checklists/authentication.md) before
shipping it.

## Implementation examples

- **Registration-time breach check**: per the
  [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html),
  reject "common and previously breached passwords." The
  [Pwned Passwords API](https://haveibeenpwned.com/API/v3#PwnedPasswords)
  implements this without exposing the candidate password: the client
  hashes the password with SHA-1 locally, sends only the first 5 hex
  characters of that hash, and receives back every suffix sharing that
  prefix along with a breach count — the service never sees the full hash,
  let alone the password.
- **Hashing parameters**: per the same cheat sheet, hash with Argon2id at
  minimum `m=19456` (19 MiB), `t=2`, `p=1`, or an equivalent configuration
  such as `m=47104`, `t=1`, `p=1`. Where Argon2id is unavailable, use
  scrypt with `N=2^17`, `r=8`, `p=1`, or bcrypt with a work factor of 10 or
  more (bcrypt truncates input at 72 bytes — reject or pre-hash longer
  passwords rather than silently truncating).
- **Password policy**: per the
  [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html),
  require a minimum of 8 characters when MFA is also enforced, or 15
  characters without MFA; allow up to at least 64 characters including
  Unicode and whitespace; and do not impose composition rules (mandatory
  symbols, mixed case) that push users toward predictable patterns.
- **Login response**: return the same message and, as far as practical, the
  same response time whether the email is unregistered or the password is
  wrong — see Common mistakes below.

## Common mistakes

### Returning different responses for "no such account" vs. "wrong password"

The OWASP Authentication Cheat Sheet requires the application to "respond
(both HTTP and HTML) in a generic manner," using a single generic message
such as "Login failed; Invalid user ID or password." It separately warns
that "[e]ven though a generic error page is shown to a user, the HTTP
response code may differ which can leak information about whether the
account is valid or not," and that "the processing time can be
significantly different according to the case (success vs failure)
allowing an attacker to mount a time-based attack." An attacker who can
distinguish the two learns which email addresses have accounts before ever
attempting to guess a password, turning a slow credential-stuffing
campaign into a targeted one. Return one uniform failure for both cases,
and keep the distinction only in server-side logs.

### Storing passwords with a fast, general-purpose hash

MD5, SHA-256, or an unsalted hash all compute in microseconds, which is
exactly the property a hash used for password storage must not have. The
OWASP Password Storage Cheat Sheet's entire set of recommended algorithms
(Argon2id, scrypt, bcrypt, PBKDF2 with 600,000+ iterations) exists because
a stolen database of fast hashes can be cracked offline at GPU speed. Hash
with Argon2id at the parameters above, per
[ADR 0001](../../decisions/0001-argon2id-for-password-hashing.md).

### Skipping the breach-password check at registration and change time

A password that has never appeared in a breach can still be guessed, but a
password that has already appeared in one is guaranteed to be in every
credential-stuffing wordlist in circulation. The OWASP Authentication
Cheat Sheet calls for blocking "common and previously breached passwords"
using a service such as Pwned Passwords. Check at registration and at
password-change time, not only at login.

## Real-world implementations

- **Have I Been Pwned**'s Pwned Passwords service is consumed directly by
  password managers and identity platforms as a drop-in registration-time
  check, exactly as described in Implementation examples above, without
  those consumers ever transmitting a user's actual password to a third
  party — the k-anonymity range query described there is the API's own
  documented integration pattern, not a hypothetical one.

## References

<!-- generated:references start -->
| Type | Source |
| --- | --- |
| Standard | [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html) |
| Standard | [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html) |
| Vendor | [Have I Been Pwned — Pwned Passwords API (k-anonymity model)](https://haveibeenpwned.com/API/v3#PwnedPasswords) |
<!-- generated:references end -->

<!-- generated:page-footer start -->
**Status:** reviewed · **Last reviewed:** 2026-09-07 · **Review due:** 2027-03-06
<!-- generated:page-footer end -->
