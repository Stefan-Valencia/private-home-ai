# Decision Log

Record decisions that affect architecture, privacy, security, hardware, or user experience. Include date, decision, reasoning, and revisit conditions.

## Initial direction

### Local-first MVP
Status: accepted as the MVP baseline.

The appliance should run inference and process documents locally by default. Remote access and cloud inference are deferred.

### Device-key access without a conventional account
Status: accepted product requirement.

The appliance must not require a conventional username/password account. Trusted-device access should use cryptographic credentials authorized locally during setup or a physical pairing action. This does not select the pairing protocol, browser/native approach, credential storage, revocation, or recovery design; those remain open under the trusted-device pairing decision.

### Inexpensive laptop before target hardware
Status: accepted as the development sequence.

Prove setup, pairing, browser UI, and a small local model on inexpensive Linux hardware before spending on the target appliance.

### EVO-X3 as evaluation target
Status: provisional.

The Ryzen AI Max+ 395 system with 128 GB unified memory is the current target for inference and appliance validation. Reconsider only if compatibility, performance, reliability, or price evidence warrants it.

### Inference runtime
Status: open.

Benchmark AMD-compatible runtimes and backends on the exact system. Do not choose a default based on model fit alone.

### Repository and model licenses
Status: CC0 1.0 Universal is present in LICENSE.

Code, model weights, datasets, and other artifacts can have different license terms. Review each separately before bundling or redistributing it.

### Onboarding simulation boundary
Status: accepted for the first Milestone 1 implementation slice (2026-10-24).

The first setup experience is a browser-only simulation with synthetic values. It does not access networking hardware, accept Wi-Fi credentials, generate keys, or authorize a real device. This lets the customer journey and state transitions be reviewed without presenting simulated behavior as appliance control. Revisit the boundary when the target Linux device is available for physical setup and recovery tests.

### Delegated PR approval and merge authority
Status: accepted at owner direction (2026-10-24).

Source: the owner's direct instruction in this conversation on 2026-10-24: “Change the project instructions so that a subagent with the project vision is allowed to do approval for merging PRs, just as before.”

An independent project-vision subagent reviews each PR against the project brief, roadmap, and decision log. When it explicitly approves, the PR is ready (not draft), its merge state is mergeable, all applicable CI and local checks have actually run and passed, and no relevant security/quality blocker or unresolved material decision needed to implement or assess that PR remains, the lead agent is authorized to merge without a second owner confirmation. For documentation-only PRs, software tests may be recorded as not applicable, but a whitespace/diff check must pass. If any applicable check is unavailable or inconclusive, do not merge. Merge stacked PRs in dependency order. This authority covers merges only; releases, external deployments, visibility changes, paid cloud spending, and material privacy/security decisions still require owner approval.

### Initial local agent and inference implementation
Status: provisional software-in-loop choice (2026-10-24).

The prototype uses Pydantic AI with its Harness `SubAgents` and `ToolGuardrail` capabilities, pinned to `pydantic-ai-harness==0.60.0`. A manager selects direct response or one bounded read-only specialist; the available specialist tools are local document search and explicitly simulated home status. The local model adapter uses an OpenAI-compatible loopback endpoint, with `llama.cpp` as the documented development server. The upstream Harness is still in the 0.x series, so keep the version pinned and compare the candidate against Qwen-Agent using the shared synthetic evaluation plan. Revisit orchestration/runtime versions after comparing a second AMD-compatible backend and running the selected model on the target hardware.

### Lexical document retrieval baseline
Status: accepted for the first AI software slice; semantic search remains open.

The local index uses SQLite FTS5 keyword search and source-page citations. It does not create embeddings. This avoids choosing or downloading an embedding model before its license, runtime support, and target-hardware cost are evaluated. Do not describe current retrieval as semantic. Revisit when the local embedding model is chosen.

### Prototype document storage boundary
Status: accepted for software-in-loop development only.

Extracted document text is stored in a local SQLite database. POSIX systems restrict the app data directory and database file to the current user; Windows inherits the per-user data directory ACL. The index is plaintext and is not encrypted at rest. Keep the service bound to loopback, disclose this limitation, and design storage encryption and recovery before alpha or shared-device use.

### Trusted-device pairing protocol and credential model
Status: open; no protocol or browser/native product choice has been approved.

The threat model and options are recorded in [THREAT_MODEL.md](THREAT_MODEL.md). A physical authorization action is necessary but does not by itself authenticate the appliance or enrolling device. Before real pairing is implemented, decide whether the first usable product must work in browsers alone or may require a native companion app, then review the complete trust bootstrap, authenticated transport, credential storage, expiry, revocation, reset, and recovery flow. Use maintained, reviewed cryptographic components; do not create a custom handshake. RFC 9846 specifies current TLS 1.3 behavior. RFC 9383 describes SPAKE2+ but states that publication does not imply IETF/IRTF endorsement. Evaluate implementations and platform fit rather than treating either reference as a product decision.

Until that decision and review, software work may test only a conspicuously labeled lifecycle simulation with synthetic identifiers. It must not generate credentials or persist trust records, and must not claim secure pairing. Revisit after browser/native constraints, the implementation library, and recovery semantics are agreed and the target device can exercise physical authorization.
### Ephemeral chat context
Status: accepted for the local software prototype (2026-10-24).

The browser keeps only completed user/assistant text turns in page memory and sends that text only to the loopback assistant service for follow-up questions. The service rejects tool, system, or other client-supplied message types. Context is limited to ten prior messages and 12,000 combined characters per request. **New chat** clears the conversation, and a page refresh also clears it. The prototype does not persist chat history in browser storage, a server session, or the document database. Revisit this behavior before adding cross-device or durable conversation history.

