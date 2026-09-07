---
title: Authentication checklist
module: authentication
status: reviewed
reviewed: 2026-09-07
tags: [Checklist, Authentication, Security]
sources:
  - { type: standard, name: "OWASP Authentication Cheat Sheet", url: "https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html" }
  - { type: standard, name: "OWASP Session Management Cheat Sheet", url: "https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html" }
---

# Authentication checklist

Every item maps to authoritative guidance so the baseline is industry
standard rather than opinion.

## Credential storage

- [ ] Passwords hashed with Argon2id — memory hardness defeats parallel cracking — [matrix](../matrices/password-hashing.md)
- [ ] Verification stays under 500 ms — a login must not become a denial-of-service lever
- [ ] No password length cap below 64 characters — caps push users toward weaker secrets
- [ ] Passwords checked against a breached-password list — reuse is the dominant real-world failure

## Session handling

- [ ] Session cookie is `HttpOnly` — script cannot read it, so XSS cannot steal it
- [ ] Session cookie is `Secure` — never transmitted over plaintext
- [ ] `SameSite=Lax` at minimum — blunts cross-site request forgery
- [ ] Session identifier is rotated on privilege change — defeats session fixation
- [ ] Logout invalidates server-side state — not just the cookie
- [ ] Idle timeout of 8 hours, absolute timeout enforced separately

## Multi-factor

- [ ] MFA is available to every account, not only administrators
- [ ] TOTP secrets encrypted at rest
- [ ] Recovery codes are single use and regenerated after use
- [ ] Enrolling or removing a factor triggers a notification to the account owner

## Rate limiting and lockout

- [ ] Login attempts limited per account and per source address
- [ ] Failures produce a uniform response — distinct errors enumerate valid accounts
- [ ] Password reset tokens are single use with a short expiry

## Verification

- [ ] Every item above has a test that fails when the control is removed

## References

<!-- generated:references start -->
| Type | Source |
| --- | --- |
| Standard | [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html) |
| Standard | [OWASP Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html) |
<!-- generated:references end -->

<!-- generated:page-footer start -->
**Status:** reviewed · **Last reviewed:** 2026-09-07 · **Review due:** 2027-03-06
<!-- generated:page-footer end -->
