# Pairing and local access threat model

Status: design review for the software-in-loop MVP (2026-10-24). This document identifies risks and decisions; it does not certify the appliance or select a pairing protocol.

## Scope and boundary

This model covers first boot, the temporary setup network, pairing a browser or companion device, access over the home network, local AI requests, document ingestion, device removal, reset, and later software updates. The current onboarding and AI services are software prototypes. They do not provision Wi-Fi, generate a real appliance identity, perform hardware-backed authorization, or establish a production network security boundary.

The appliance boundary contains the operating system, setup and chat services, local inference service, document database and index, network configuration, trusted-device records, and future update/recovery mechanism. Outside it are the owner's phone and computers, home router, other devices on the home LAN, nearby radio users during setup, model and software suppliers, and the public internet. The baseline product does not expose remote access or depend on a cloud service.

## Assets to protect

- Documents, extracted text, prompts, responses, and local indexes.
- Appliance identity and private keys; trusted-device credentials and recovery material.
- Home Wi-Fi credentials and setup-network secrets.
- Update signing keys, installed software, model configuration, and recovery state.
- User control over which devices are trusted and the ability to remove a lost device.
- Accurate user understanding of what is simulated, stored locally, or exposed on a network.

## Adversaries and assumptions

Consider an untrusted device on the same home network, a nearby person able to join or observe the setup network, a stolen or compromised trusted phone, a malicious document or model artifact, and an attacker able to send requests to exposed services. Also consider accidental loss, interrupted power, and incorrect recovery actions.

For this MVP model, assume the owner can physically reach the appliance during initial setup and recovery. Do not assume that the home Wi-Fi is trustworthy, that a network name proves appliance identity, or that a browser profile is a durable hardware identity. Physical access after setup, root compromise, radio jamming, compromised upstream signing infrastructure, and hardware supply-chain compromise are not prevented by the current prototype; describe these limits rather than claiming they are solved.

## Security goals

1. Pairing is possible only during a short, explicit physical authorization window.
2. The pairing exchange proves the intended appliance and the enrolling device to each other, binds the new credential to that exchange, resists replay, and has bounded online guessing attempts.
3. Pairing material expires and is consumed once. A removed device cannot regain access with its old credential.
4. Local traffic is protected against observation and modification by other LAN participants; the service rejects untrusted origins and does not silently fall back to cloud inference.
5. Logs, model context, tool results, errors, and user-visible diagnostics do not disclose device secrets, Wi-Fi credentials, or document contents unnecessarily.
6. Reset and recovery have documented consequences for identity, paired devices, stored documents, and availability.
7. Authentication and authorization are enforced by the service boundary, not by model instructions or a UI-only check.

These are design goals. Each requires an implementation and test before it can be claimed as a product property.

## Threats and required controls

| Threat | Likely impact | Required control or evidence | Current status |
| --- | --- | --- | --- |
| Fake setup page or active LAN interception | Credentials or pairing data sent to an attacker; false appliance identity | Authenticate the appliance before enrollment; bind enrollment to the intended device; use a reviewed secure channel and test hostile-network cases | Open design; current setup is a synthetic browser simulation |
| Pairing from an unauthorized LAN client | Attacker gains access to documents or chat | Physical authorization window, short expiry, one-use enrollment, rate limiting, and server-side checks on every protected request | No real pairing or trusted-device store exists |
| Replayed, guessed, photographed, or relayed setup code | Unauthorized enrollment or takeover | Use sufficient entropy or a reviewed PAKE for short codes; bind both sides to the same exchange; cap attempts; expire and invalidate on use/reset | Protocol and code UX are open |
| Lost or compromised trusted device | Continued access to local data | Show understandable device names and last-used details; revoke immediately; expire credentials; document what happens to browser-held keys and cached data | Management and revocation are not implemented |
| Browser token theft, cross-site requests, or malicious local web content | Attacker acts as a trusted user | Minimize credential exposure to scripts; use browser-appropriate cookie and origin protections; apply least privilege, CSP, CSRF defenses where applicable, and reauthentication for sensitive changes. Origin checks restrict browser request sources; they do not authenticate a trusted device or replace server-side authorization. | Prototype has loopback/origin protections; device authentication is absent |
| Untrusted same-LAN traffic | Eavesdropping, request modification, or service abuse | Authenticated encrypted transport and strict service binding; host/origin validation; request limits; no trust based on private IP addresses alone | Prototype is loopback-only; real LAN behavior untested |
| Malicious document or prompt injection | False answers, secret disclosure, or unauthorized actions | Treat documents and model output as untrusted; enforce a narrow server-side tool allowlist; bound parsers; do not place secrets in model context | Synthetic injection and bounded-upload checks exist; real-model behavior remains unmeasured |
| Compromised model, inference runtime, or third-party dependency | Local data disclosure, unsafe output, or control of the appliance process | Pin and verify dependencies and model revisions; review licenses and provenance; isolate inference; give it no credentials or broad filesystem/network access; measure and review updates | Prototype uses pinned Python dependencies and a local-compatible API; runtime, model provenance, isolation, and supply-chain controls are not yet production-validated |
| Database or appliance theft | Offline exposure of documents, credentials, and prompts | Decide storage encryption and key recovery; minimize retained data; explain physical-theft limits | Prototype SQLite index is plaintext; storage protection is open |
| Malicious or rolled-back update | Persistent compromise or weakened security | Signed updates, protected signing keys, version/rollback policy, verified recovery image, and update-failure tests | Not implemented |
| Reset or recovery misuse | Owner lockout, residual access, or accidental data loss | Explicit reset semantics, credential revocation/key rotation, backup expectations, and a verified recovery path | Open; target hardware unavailable |
| Logs, crash reports, or diagnostics leak secrets | Private content or credentials exposed to local users or support channels | Redact by design; return generic errors for unexpected model/backend failures; do not transmit telemetry by default; inspect logs and crash paths using synthetic canaries | The chat API returns a generic message for unexpected failures and exposes only explicitly typed safe assistant errors; full appliance logging review remains open |

## Pairing design choices that require a product/security decision

The physical action and the network authentication protocol are separate controls. A button or equivalent hardware event authorizes an attempt; it does not itself prove which device is connecting or secure the connection.

| Direction to evaluate | Benefits | Costs and risks to test |
| --- | --- | --- |
| Browser-only enrollment with an out-of-band QR or one-time code | No companion app to install; familiar setup flow | Browser certificate and credential handling varies; bootstrapping trust against a fake page or relay is difficult; persistent credential storage and recovery need explicit design |
| Native companion app with QR bootstrap and OS-protected device keys | Can use platform key storage and present a purpose-built recovery/removal flow | Requires app development, platform support, distribution, and maintenance; availability and behavior differ by platform |
| Short code with a reviewed PAKE, then standard channel credentials | Can avoid sending the short code as a reusable password and can authenticate a short human-readable secret | Requires a maintained, reviewed implementation; careful rate limits, relay resistance, server identity binding, and browser compatibility; the code must still be protected physically |

TLS 1.3 is specified as a secure channel with server authentication and optional client authentication; its current IETF specification is RFC 9846. A PAKE is a separate enrollment option, not a substitute for lifecycle controls. SPAKE2+ is described by RFC 9383, which explicitly says it was produced outside the IETF/IRTF and does not imply IETF or IRTF endorsement. This project should select a maintained implementation only after platform and threat review, and must not invent a custom handshake.

Before implementation, decide whether browser-only support is required for the first usable product or a native companion app is acceptable. Then review the exact bootstrap, transport, credential storage, revocation, expiry, reset, and recovery design together. No option is selected by this document.

### Minimum review and acceptance criteria for a selected design

- **Credential protection:** document where every private key and session credential lives, whether application scripts can read it, how it is protected at rest, and how an owner clears it. No long-lived secret may be placed in model context, URLs, logs, or ordinary diagnostic output.
- **Enrollment limits:** specify and test a server-enforced attempt cap and backoff/window policy. Expired and consumed material must fail. A replay must fail, and concurrent use must produce at most one enrollment.
- **Revocation:** after removal is acknowledged, the removed device's next protected request must fail. Define how sessions, refresh credentials, and cached browser state are invalidated.
- **Recovery:** specify how the owner regains control after losing every paired device, whether appliance identity changes, what data is retained or erased, and how all prior credentials are invalidated. Test interrupted and repeated recovery.
- **Network trust:** define how the enrolling device identifies the intended appliance before sending a credential, and test against a spoofed setup endpoint and an active untrusted-LAN attacker.
- **Separation of authority:** demonstrate that an unauthenticated request cannot read documents or invoke tools, even when the model requests it. Browser Origin checks alone do not meet this requirement.
- **Evidence and limits:** obtain independent review of the exact library versions and protocol composition; list unsupported clients and remaining physical or supply-chain assumptions.

The numeric attempt limit and cooldown, browser/native credential mechanism, and recovery policy remain open until the candidate design is reviewed. The test harness should read those values from the selected policy and verify the documented behavior, not invent values during implementation.

## Safe software-only work while hardware is unavailable

Progress can continue with a clearly labeled simulation that uses synthetic device names and identifiers only. Keep the “Simulation only” disclosure visible in every state, including active authorization, enrolled, expired, revoked, reset, error, and retry states. It can exercise the owner-facing lifecycle—start a simulated authorization window, enroll a simulated device, list devices, revoke one, expire an invitation, and reset the simulation—and reject invalid transitions. It must not generate or persist real credentials or trust records, read a physical button, claim network authentication, or present itself as secure pairing. A later implementation must replace the simulated authorization input with a tested hardware event and an approved protocol.

## Evidence needed before security claims

- Software tests for authorization-window expiry, one-use behavior, replay, attempt limits, invalid transitions, revocation, reset, and concurrent enrollment.
- Independent review of the selected protocol, libraries, browser/native credential handling, server authorization boundary, and recovery flow.
- Network tests against an untrusted LAN client and a spoofed setup endpoint.
- Physical tests for button timing, reset, power loss, setup-network exposure, and recovery on the target appliance.
- Storage, update-signature, downgrade, and recovery tests on the selected hardware and operating system.

Passing simulation tests are evidence about the simulation only. They do not establish physical authorization, real cryptographic pairing, secure storage, or production readiness.

## References

- [RFC 9846: The Transport Layer Security (TLS) Protocol Version 1.3](https://www.rfc-editor.org/rfc/rfc9846.html)
- [RFC 9383: SPAKE2+, an Augmented Password-Authenticated Key Exchange (PAKE) Protocol](https://www.rfc-editor.org/rfc/rfc9383.html)
