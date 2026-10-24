# MVP Test Plan

This plan defines evidence to gather; it does not claim any checks have already run.

## Development-only onboarding simulation
- Verify the state machine follows welcome, temporary setup network, demo identity, simulated physical pairing, test-network selection, connection success/failure, retry, ready, and reset states.
- Verify invalid transitions fail at every stage and reset returns to the initial state, including from partial setup.
- Confirm the simulation does not ask for passwords or access Wi-Fi hardware, and that its content policy blocks outbound connections.
- Keep simulated pairing visibly distinct from actual hardware authorization.
- Test that keyboard focus moves to the new step heading and that progress labels remain readable on mobile.

## First-boot and network
- Reset to the uninitialized state and complete setup using a phone.
- Confirm the temporary setup network is discoverable and the local setup page is reachable.
- Configure home Wi-Fi, verify reconnect after reboot, and confirm setup mode does not remain unnecessarily open.
- Exercise wrong credentials, unavailable router, interrupted setup, restart, and power-loss recovery.
- Test with representative Android and iOS browsers plus a desktop browser.

## Identity and device pairing
- Confirm each initialization creates a fresh appliance identity.
- Verify pairing requires a physical authorization window.
- Verify expired pairing material is rejected.
- Verify unauthorized devices cannot pair, and removed devices lose access.
- Review logs and storage for accidental secrets or pairing material.

## Local AI and documents
- Verify chat works locally and remains available without internet after setup.
- Upload synthetic text and PDF documents; verify extraction, retrieval, and source references.
- Test unsupported, oversized, malformed, and encrypted files with clear user errors.
- Confirm prompts, documents, embeddings, and indexes remain local by default.

## Software-in-loop assistant checks
- Exercise direct response and one manager-to-specialist document-search flow with deterministic fake models.
- Confirm specialist results and retrieved excerpts are labeled as untrusted evidence and a prohibited tool handler never runs, including when a deterministic model attempts an unauthorized action after seeing an injected document.
- Run `python -m home_ai.evaluate --retrieval-only` and record the fixed synthetic set's FTS5 Recall@5 against the proposed 90% gate.
- When a local model is available, run `python -m home_ai.evaluate` and record route accuracy, citation accuracy, required-term accuracy, abstention accuracy, synthetic-canary non-disclosure, p50/p95 latency, model revision, and serving settings. This command accepts only a validated loopback inference endpoint and does not download weights.
- Confirm proxy environment variables cannot redirect inference or health requests, redirects are rejected, and API Host/Origin checks reject browser cross-origin requests.
- Test per-page and cumulative compressed PDF expansion limits, database permissions on POSIX, local-index removal, upload limits, and citation preservation.
- Send an incomplete upload and confirm its total body-read deadline lets server shutdown finish.
- Build a wheel and confirm the packaged evaluation module and its HTML, JavaScript, and CSS assets are present.
- Record that fake-model results do not prove real-model answer quality, offline behavior, speed, or target-hardware compatibility.

## Model and hardware benchmark
For each model/runtime/backend combination, record:
- Hardware, BIOS settings, OS, kernel, driver, and runtime versions.
- Model source, model license, parameter/MoE configuration, quantization, and context length.
- Peak memory, time to first token, prompt processing speed, generation tokens per second, and task quality.
- Power draw, temperatures, fan behavior, and performance after sustained load.

Use a fixed synthetic prompt set. Compare model sizes and quantizations on the actual target hardware; cloud RAM capacity tests are not evidence of unified-memory performance.

## Security and recovery
- Threat-model first boot, pairing, local-network access, device theft, storage loss, updates, and recovery.
- Verify update signature checks, rollback behavior, and documented recovery path before production claims.
- Run an independent review of pairing and authentication before calling the appliance production-ready.

## Software-only pairing lifecycle simulation
- Use conspicuously synthetic device names and identifiers; create no keys, credentials, network access, or persisted trust records.
- Exercise simulated authorization-window start, expiry, one-use enrollment, list, revoke, reset, and invalid transitions.
- Keep a visible “Simulation only” label in enrolled, expired, revoked, and reset states; do not use “trusted” or “authenticated” for simulated devices.
- Check that keyboard focus and screen-reader announcements make enrollment, expiry, revocation, and reset state changes clear.
- Keep the simulation results separate from the physical-button, cryptographic protocol, network interception, credential storage, and recovery evidence above.
