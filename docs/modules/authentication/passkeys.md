---
title: Passkeys
module: authentication
status: reviewed
reviewed: 2026-09-07
tags: [Authentication, Passwordless, Passkeys]
sources:
  - { type: standard, name: "W3C Web Authentication (WebAuthn) Level 3", url: "https://www.w3.org/TR/webauthn-3/" }
  - { type: vendor, name: "FIDO Alliance — Passkeys", url: "https://fidoalliance.org/passkeys/" }
  - { type: vendor, name: "Google Account Help — Sign in with a passkey instead of a password", url: "https://support.google.com/accounts/answer/13548313" }
---

# Passkeys

## Executive summary

### Purpose

A passkey is a FIDO/WebAuthn public-key credential: a relying party (the
application) stores a public key at registration, the private key never
leaves the user's authenticator, and every login is a cryptographic
challenge-response signed by that private key. There is no shared secret
in transit or at rest to phish, guess, or leak from a breached database.

### When to use

Use passkeys as the primary credential for any product where the client
platform supports WebAuthn (essentially every modern browser and mobile
OS) and where phishing resistance matters — anything handling money,
health data, or account recovery for other systems. Offer them as an
upgrade path immediately after first login via
[email/password](email-password.md) or [magic link](magic-link.md), as the
[module overview](index.md#implementation-examples) describes.

### When not to use

- The client is a constrained or legacy device without a WebAuthn-capable
  browser or platform authenticator — there is no fallback within this
  mechanism itself; you need a second mechanism such as
  [email/password](email-password.md) for those clients.
- The product cannot yet build or test an account-recovery path. A user
  who loses every device holding a passkey and never registered a second
  authenticator is locked out by design — see Common mistakes below.
- The relying party's domain will change (a rebrand, a domain migration).
  WebAuthn credentials are bound to the origin they were registered under,
  by design, and do not transfer automatically to a new one.

## How it works

``` mermaid
sequenceDiagram
  autonumber
  actor User
  participant App as Relying party (App)
  participant Browser
  participant Auth as Authenticator
  Note over User,Auth: Registration
  User->>App: request registration
  App->>Browser: challenge + relying party ID
  Browser->>Auth: create credential (origin-bound)
  Auth->>Auth: generate key pair, store private key
  Auth-->>Browser: public key + attestation
  Browser-->>App: public key + attestation
  App->>App: store public key, verify origin
  Note over User,Auth: Authentication
  User->>App: request login
  App->>Browser: challenge
  Browser->>Auth: sign challenge (user verification: biometric/PIN)
  Auth-->>Browser: signed assertion
  Browser-->>App: signed assertion
  App->>App: verify signature against stored public key
  App-->>User: session (see session-cookies.md)
```

## Pros and cons

- **Pro**: cannot be phished the way a password or a one-time code can,
  because the credential is bound to the origin that registered it — a
  lookalike domain simply cannot obtain a valid signature, regardless of
  how convincing the page is to the user.
- **Pro**: nothing secret is stored server-side. A stolen database of
  passkey public keys is useless to an attacker; there is no password-hash
  cracking risk analogous to [email/password](email-password.md).
- **Pro**: synced passkeys (FIDO Alliance's term for credentials backed up
  through a platform credential manager such as iCloud Keychain or Google
  Password Manager) survive losing a single device, unlike a device-bound
  hardware key.
- **Con**: synced passkeys trade some assurance for that convenience — FIDO
  Alliance itself notes that device-bound passkeys on security keys offer
  "the highest security assurance" precisely because they cannot leave the
  device or sync through a cloud account.
- **Con**: account recovery is a genuinely new design problem. There is no
  "forgot passkey" analog to a password reset email; losing access to
  every enrolled authenticator requires a deliberate recovery path.
- **Con**: requires client platform support. Older browsers and some
  embedded or kiosk environments cannot complete a WebAuthn ceremony at
  all.

## Alternatives

- **[Email/password](email-password.md)** works everywhere but carries the
  stored-secret and phishing risk passkeys are designed to remove.
- **[Magic link](magic-link.md)** removes the stored secret but keeps a
  phishable delivery channel (the email link itself can be relayed to a
  fake site by an attacker faster than the user notices).
- **[Social login](social-login.md) or [enterprise SSO](enterprise-sso.md)**
  delegate the credential problem entirely, at the cost of depending on
  the provider's availability and account model.

## Security considerations

- [MFA](../../security/mfa.md) — a passkey satisfies both "something you
  have" (the authenticator) and, when it requires biometric or PIN user
  verification, "something you are/know," but confirm this against your
  own MFA policy rather than assuming it by default.
- [Session security](../../security/session-security.md) — what the
  verified assertion becomes after the ceremony completes.
- Recovery paths for lost authenticators need the same scrutiny as any
  other account-recovery flow; treat them as a first-class part of the
  design, not an afterthought bolted on after launch. Run the design
  against the [authentication checklist](../../checklists/authentication.md).

## Implementation examples

- **Registration ceremony**: per
  [WebAuthn Level 3](https://www.w3.org/TR/webauthn-3/), the relying party
  sends a challenge and its relying party ID to the browser, which asks
  the authenticator to create a public key credential; the authenticator
  generates a key pair, keeps the private key, and returns the public key
  plus attestation for the server to store and verify.
- **Discoverable credentials**: to support "sign in with a passkey"
  without the user typing a username first, request a client-side
  discoverable credential (what WebAuthn Level 3 calls the modern name for
  what was historically called a resident key) — "usable in authentication
  ceremonies where the Relying Party does not provide any credential IDs."
  This is what enables the passwordless, username-less autofill flow.
- **Assurance tiering**: for the highest-value actions, distinguish synced
  from device-bound passkeys at verification time and step up to a
  device-bound authenticator (a security key) where FIDO Alliance's
  highest-assurance guidance applies, rather than treating every passkey
  as equivalent.
- **Recovery enrollment**: require at least two enrolled authenticators
  (for example, a platform passkey and a hardware security key) before
  disabling other login methods for an account, so a single lost device
  does not equal a locked-out account.

## Common mistakes

### Shipping passkey login with no account-recovery design

There is no "forgot passkey" email, because there is no shared secret to
reset. If a user's only enrolled device is lost, stolen, or wiped, and no
recovery path was designed in, the account is unrecoverable through this
mechanism alone. FIDO Alliance's guidance is direct about the fix: enroll
device-bound passkeys on security keys as recovery credentials, because,
in the Alliance's words, "using security keys eliminates the need for weak
backup codes or helpdesk resets." Design and test the recovery path — a
second enrolled authenticator, a
recovery security key, or a fallback to a verified
[email/password](email-password.md) or [enterprise SSO](enterprise-sso.md)
account — before passkeys become the only way in.

### Treating every passkey as equally strong evidence of identity

A synced passkey backed up through a cloud credential manager and a
device-bound passkey on a hardware security key are not the same
assurance level, even though both satisfy a WebAuthn ceremony. FIDO
Alliance is explicit that device-bound passkeys offer "the highest
security assurance." An application that grants identical trust to both
gives up the ability to require the stronger option for its most sensitive
actions. Distinguish them where the authenticator reports it, and require
the higher-assurance form for account recovery and high-value operations.

### Assuming a passkey registered on one origin will "just work" on another

WebAuthn credentials are cryptographically bound to the relying party
origin at registration time — this is precisely why they cannot be
phished by a lookalike domain. It also means a domain migration or brand
change invalidates every previously registered passkey unless the new
origin is planned for in advance. Plan relying party ID and origin
strategy before launch, not after a migration breaks every user's login.

## Real-world implementations

- **Google** has [made passkeys the default sign-in
  option](https://support.google.com/accounts/answer/13548313) for
  personal accounts, positioning them as a replacement for passwords
  rather than an optional add-on — the direction this page recommends via
  the passwordless-funnel pattern in the
  [module overview](index.md#implementation-examples).
- **FIDO Alliance**, as the standards body behind the WebAuthn credential
  model, publishes the synced-vs-device-bound distinction this page's
  Common mistakes section relies on, and explicitly recommends
  device-bound security keys as the recovery mechanism for accounts that
  have gone all-in on passkeys.

## References

<!-- generated:references start -->
| Type | Source |
| --- | --- |
| Standard | [W3C Web Authentication (WebAuthn) Level 3](https://www.w3.org/TR/webauthn-3/) |
| Vendor | [FIDO Alliance — Passkeys](https://fidoalliance.org/passkeys/) |
| Vendor | [Google Account Help — Sign in with a passkey instead of a password](https://support.google.com/accounts/answer/13548313) |
<!-- generated:references end -->

<!-- generated:page-footer start -->
**Status:** reviewed · **Last reviewed:** 2026-09-07 · **Review due:** 2027-03-06
<!-- generated:page-footer end -->
