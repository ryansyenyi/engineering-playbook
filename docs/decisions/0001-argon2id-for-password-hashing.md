---
title: Use Argon2id for password hashing
module: authentication
status: reviewed
reviewed: 2026-09-07
tags: [ADR, Authentication, Security]
sources:
  - { type: rfc, name: "RFC 9106 — Argon2", url: "https://www.rfc-editor.org/rfc/rfc9106" }
  - { type: standard, name: "OWASP Password Storage Cheat Sheet", url: "https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html" }
---

# Use Argon2id for password hashing

## Context

Password storage must stay expensive for an attacker holding a stolen
database and cheap enough for a login request. bcrypt has served this role
but is not memory hard and silently truncates input past 72 bytes. PBKDF2 is
weakest against parallel hardware and is chosen almost entirely for
compliance reasons.

## Decision

Argon2id is the default for all new password storage, with parameters tuned
so verification stays under 500 ms on production hardware.

## Consequences

### Positive

Memory hardness removes the attacker's parallel-hardware advantage. Argon2id
combines Argon2i's side-channel resistance with Argon2d's GPU resistance.
The algorithm is standardized in RFC 9106 and recommended first by OWASP.

### Negative

Verification consumes real memory per concurrent login, which constrains how
many logins a node handles at once. Parameters must be re-tuned when hardware
changes, and that re-tuning is easy to forget.

## Alternatives considered

See [the password hashing matrix](../matrices/password-hashing.md).

## Migration path

Rehash opportunistically on successful login. Store the algorithm identifier
with each hash so both schemes coexist during the transition.

## References

<!-- generated:references start -->
| Type | Source |
| --- | --- |
| RFC | [RFC 9106 — Argon2](https://www.rfc-editor.org/rfc/rfc9106) |
| Standard | [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html) |
<!-- generated:references end -->

<!-- generated:page-footer start -->
**Status:** reviewed · **Last reviewed:** 2026-09-07 · **Review due:** 2027-03-06
<!-- generated:page-footer end -->
