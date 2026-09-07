---
title: Password hashing
module: authentication
status: reviewed
reviewed: 2026-09-07
tags: [Decision matrix, Authentication, Security]
sources:
  - { type: rfc, name: "RFC 9106 — Argon2", url: "https://www.rfc-editor.org/rfc/rfc9106" }
  - { type: standard, name: "OWASP Password Storage Cheat Sheet", url: "https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html" }
---

# Password hashing

<!-- generated:matrix start -->
| Option | Resistance to GPU attack | Memory hard | Standardized | Score | Verdict |
| --- | --- | --- | --- | --- | --- |
| Argon2id | Strong | Yes | RFC 9106 | 5 | Default choice |
| scrypt | Strong | Yes | RFC 7914 | 4 | Good where Argon2id is unavailable |
| bcrypt | Moderate | No | De facto | 3 | Acceptable legacy; 72-byte input limit |
| PBKDF2 | Weak | No | NIST SP 800-132 | 2 | Only when FIPS compliance forces it |
<!-- generated:matrix end -->

## Why

Password hashing is chosen for how badly it performs on an attacker's
hardware. Argon2id wins because it is memory hard: an attacker cannot trade
cheap parallel compute for the memory the algorithm demands, which is exactly
the advantage GPUs and ASICs otherwise have.

## Tradeoffs

Memory hardness costs the defender memory too. Tune the parameters against
your own hardware and keep verification within the latency budget.

## Migration path

Rehash on successful login: verify against the old algorithm, then write a
fresh Argon2id hash. Store the algorithm alongside the hash so both can
coexist during the transition. Never bulk-rehash — you do not have the
plaintext.

See [Use Argon2id for password hashing](../decisions/0001-argon2id-for-password-hashing.md).

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
