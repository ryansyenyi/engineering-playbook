---
title: Enterprise SSO
module: authentication
status: reviewed
reviewed: 2026-09-07
tags: [Authentication, SSO, SAML]
sources:
  - { type: standard, name: "OASIS SAML 2.0 — Assertions and Protocols for the OASIS Security Assertion Markup Language (SAML) V2.0", url: "https://docs.oasis-open.org/security/saml/v2.0/saml-core-2.0-os.pdf" }
  - { type: standard, name: "OWASP SAML Security Cheat Sheet", url: "https://cheatsheetseries.owasp.org/cheatsheets/SAML_Security_Cheat_Sheet.html" }
  - { type: vendor, name: "Microsoft Learn — Microsoft Entra Conditional Access overview", url: "https://learn.microsoft.com/en-us/entra/identity/conditional-access/overview" }
---

# Enterprise SSO

## Executive summary

### Purpose

Enterprise SSO federates authentication to a customer's own identity
provider — typically via SAML 2.0, sometimes via [OIDC](oidc.md) — so that
a company's employees sign in with the credentials and policies their IT
department already controls, rather than a credential your application
issues and stores. Your application becomes a SAML service provider (SP)
trusting assertions issued by the customer's identity provider (IdP).

### When to use

Use it once you are selling to organizations whose IT or security team
requires centralized identity control: provisioning and deprovisioning
through their directory, their own MFA and conditional-access policies
applied to your application, and an audit trail that lives in systems they
already run. This is the point at which
[email/password](email-password.md) accounts per employee become a
liability the customer's security team will flag.

### When not to use

- The customer base is individual consumers, not organizations with an
  identity team. There is no IdP to federate with, and
  [social login](social-login.md) or [email/password](email-password.md)
  serves that audience better.
- You cannot commit to per-tenant configuration and testing. Every
  customer's IdP (Okta, Entra ID, Ping, a homegrown SAML IdP) has its own
  quirks in assertion format, clock skew tolerance, and attribute naming;
  treating SAML as a single integration done once is how the signature-
  validation flaws in Common mistakes get shipped.
- The integration cannot budget time for signature and assertion
  validation done correctly. A SAML implementation that parses first and
  validates second is a bigger liability than not offering SSO at all —
  see Common mistakes.

## How it works

``` mermaid
sequenceDiagram
  autonumber
  actor User
  participant SP as Your app (service provider)
  participant Browser
  participant IdP as Customer's identity provider
  User->>SP: request protected resource
  SP->>Browser: redirect to IdP with AuthnRequest
  Browser->>IdP: AuthnRequest (HTTP-Redirect binding)
  IdP->>User: authenticate (+ IdP's own MFA / conditional access)
  User->>IdP: approve
  IdP->>Browser: signed SAML Response (HTTP-POST binding)
  Browser->>SP: POST SAML Response
  SP->>SP: validate signature, Issuer, AudienceRestriction, NotOnOrAfter
  SP->>SP: confirm exactly one Assertion, reference matches signed ID
  alt valid
    SP-->>User: session (see session-cookies.md)
  else invalid
    SP-->>User: reject, no session issued
  end
```

## Pros and cons

- **Pro**: the customer's IT team owns provisioning, deprovisioning, and
  policy — an employee who leaves the company loses access the moment
  their directory account is disabled, without your application doing
  anything.
- **Pro**: the customer's own conditional-access controls (device
  compliance, location, risk signals) apply to your application "for
  free," inheriting whatever policy their security team has already
  built.
- **Con**: SAML's assertion format is XML, and XML signature validation is
  notoriously easy to implement in a way that "verifies" without actually
  binding the verified signature to the data your code reads — see Common
  mistakes.
- **Con**: every customer IdP is a slightly different integration.
  Multi-tenant SP configuration, metadata rotation, and certificate
  expiry all become operational surface area that a single shared login
  flow does not have.
- **Con**: your login availability now depends on the customer's IdP
  being reachable, not just your own infrastructure.

## Alternatives

- **[OIDC](oidc.md)** as the federation protocol instead of SAML, where
  the customer's IdP supports it — JSON and JWT-based rather than
  XML-based, which removes the XML-signature-wrapping class of bug
  entirely.
- **[Social login](social-login.md)** if the "enterprise" in question is
  small enough that its members authenticate with personal provider
  accounts rather than a managed directory.
- **[Email/password](email-password.md)** as the fallback for any
  customer that has not configured an identity provider yet — the
  [module overview](index.md#implementation-examples) recommends keeping
  this path rather than blocking accounts entirely on SSO being
  configured.

## Security considerations

- [SSO](../../security/sso.md) — federation-specific hardening beyond
  what this page covers.
- [OAuth security](../../security/oauth-security.md) — relevant wherever
  the SSO integration is OIDC-based rather than SAML-based.
- [Session security](../../security/session-security.md) — what a
  validated assertion becomes once the SP accepts it.
- [Audit logging](../../security/audit-logging.md) — enterprise buyers
  frequently require this as a contractual condition of SSO, not just a
  security nicety.

Every SSO integration should pass the
[authentication checklist](../../checklists/authentication.md) before a
customer is allowed to enable it.

## Implementation examples

- **Assertion validation order**: SAML 2.0 core §2.3.3 states, "If such a
  signature is used, then the `<ds:Signature>` element MUST be present,
  and a relying party MUST verify that the signature is valid (that is,
  that the assertion has not been tampered with) in accordance with
  [XMLSig]," and, "If it is invalid, then the relying party MUST NOT rely
  on the contents of the assertion." Do this before reading any value out
  of the assertion, not after, and reject the entire response if
  validation fails.
- **Audience and time-window checks**: validate the `AudienceRestriction`
  element matches your service provider's own entity ID, and that the
  current time falls within the assertion's validity window. SAML 2.0
  core §2.5.1.2 defines that window — "The NotBefore attribute specifies
  the time instant at which the validity interval begins. The
  NotOnOrAfter attribute specifies the time instant at which the validity
  interval has ended" — and §2.5.1.4 defines the audience check: "The
  audience restriction condition evaluates to Valid if and only if the
  SAML relying party is a member of one or more of the audiences
  specified." An assertion issued for a different SP, or replayed outside
  its validity window, must be rejected regardless of a valid signature.
- **Single-assertion enforcement**: per the
  [OWASP SAML Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/SAML_Security_Cheat_Sheet.html)
  guidance on signature wrapping, reject any SAML response containing more
  than one `Assertion` element, and confirm the signature's Reference URI
  points at the exact assertion ID your code then reads — never the first
  or last assertion found anywhere in the document.
- **Conditional access as a customer-side control**: document for
  customers that policies such as
  [Microsoft Entra Conditional Access](https://learn.microsoft.com/en-us/entra/identity/conditional-access/overview)
  are "enforced after first-factor authentication is completed" on the
  IdP side — your SP does not need to reimplement device compliance or
  location checks; it needs to trust the IdP's assertion once validated.

## Common mistakes

### Validating the signature on one element and reading data from another

This is the core of an XML Signature Wrapping (XSW) attack: an attacker
submits a response containing a validly signed assertion somewhere in the
document, plus a second, unsigned or modified assertion elsewhere, and
relies on the service provider's parser reading the wrong one — for
example, the first `Assertion` it finds, rather than the one the signature
actually covers. This happens when signature verification and assertion
processing are handled as separate steps against separate parses of the
same XML, letting an attacker change a role from guest to administrator
while the signature still "verifies" in the narrow sense SAML 2.0 core
§2.3.3 requires — the section mandates that the relying party "MUST
verify that the signature is valid" and, if not, "MUST NOT rely on the
contents of the assertion," but says nothing about which assertion
element in a multi-assertion document that verification result should be
trusted for. That binding is exactly what the
[OWASP SAML Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/SAML_Security_Cheat_Sheet.html)
closes: check that the signature's Reference URI matches the ID of the
assertion your code reads, reject documents with more than one assertion,
and use a single hardened XML parser with DTDs disabled for the whole
pipeline.

### Skipping `AudienceRestriction` or `NotOnOrAfter` validation

A signature proves the assertion was issued by the expected IdP; it says
nothing about who the assertion was issued for or how long it remains
valid. SAML 2.0 core §2.5.1 defines `Conditions`, with §2.5.1.2 governing
the `NotBefore`/`NotOnOrAfter` validity window and §2.5.1.4 governing
`AudienceRestriction` (quoted above in Implementation examples) —
precisely so a service provider can reject an assertion that is validly
signed but was issued for a different application, or has already
expired. Skipping either check accepts an assertion your application was
never the intended recipient of, or replays one long after it should have
stopped being trusted. Validate every `Conditions` child element, not
only the signature.

### Treating SSO configuration as a one-time integration per identity provider

Metadata (certificates, endpoint URLs) rotates on the IdP side on its own
schedule, and a certificate rotation your SP does not pick up fails closed
— or, worse, fails open if the validation code was written to tolerate
unknown certificates rather than reject them. Enterprise customers running
[Microsoft Entra Conditional Access](https://learn.microsoft.com/en-us/entra/identity/conditional-access/overview)
policies also change those policies independently of your integration.
Monitor certificate expiry, support metadata refresh, and treat each
customer's SSO configuration as something that needs ongoing operational
ownership, not a checkbox ticked once at onboarding.

## Real-world implementations

- **Microsoft Entra** documents that
  [Conditional Access](https://learn.microsoft.com/en-us/entra/identity/conditional-access/overview)
  policies are "if-then statements" evaluated after first-factor
  authentication, combining signals such as user, device state, location,
  and sign-in risk to grant, block, or require additional controls like
  MFA or a compliant device — this is the customer-side policy layer that
  sits in front of the SAML or OIDC assertion your service provider
  ultimately validates, and it is why the same enterprise-SSO integration
  can behave differently for the same user depending on the customer's
  own configured policy.

## References

<!-- generated:references start -->
| Type | Source |
| --- | --- |
| Standard | [OASIS SAML 2.0 — Assertions and Protocols for the OASIS Security Assertion Markup Language (SAML) V2.0](https://docs.oasis-open.org/security/saml/v2.0/saml-core-2.0-os.pdf) |
| Standard | [OWASP SAML Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/SAML_Security_Cheat_Sheet.html) |
| Vendor | [Microsoft Learn — Microsoft Entra Conditional Access overview](https://learn.microsoft.com/en-us/entra/identity/conditional-access/overview) |
<!-- generated:references end -->

<!-- generated:page-footer start -->
**Status:** reviewed · **Last reviewed:** 2026-09-07 · **Review due:** 2027-03-06
<!-- generated:page-footer end -->
