# MVP Roadmap

The roadmap is ordered to prove the customer journey cheaply before optimizing the target appliance. Keep each milestone reviewable and update this file as evidence changes the plan.

## Milestone 0: Product and repository foundation
- Keep acceptance criteria, open decisions, and threat-model questions in the repository.
- Record the CC0 repository license and track model and dataset terms before distributing those artifacts.
- Establish reproducible development and documentation conventions.

Exit evidence: a reviewed project brief and a test plan with clear success measures.

## Milestone 1: First-boot setup prototype on inexpensive Linux hardware
- Start with a clearly labeled UI/state-machine simulation that uses only synthetic state; it must not enable Wi-Fi, create real keys, or collect network credentials.
- Create the temporary Wi-Fi access point.
- Serve a phone-friendly local setup page.
- Configure and join the home Wi-Fi network.
- Simulate the physical pairing button if the laptop lacks one.
- Test setup from a factory-reset state on real phones.

Exit evidence: repeatable phone-to-appliance onboarding with reset and recovery instructions.

Current status: the browser-only simulation is implemented. Access-point provisioning, home Wi-Fi recovery, and phone testing remain unverified and require the target Linux appliance.

## Milestone 2: Local identity and trusted-device flow
- Generate a fresh local appliance identity during initialization.
- Require an explicit physical action to authorize device pairing.
- Implement add, remove, expiry, and recovery behavior for trusted devices.
- Review the threat model before making security claims.

Exit evidence: authorized and unauthorized pairing cases are documented and tested.

## Milestone 3: Local AI and document question answering
- Build the browser chat interface and local inference service.
- Evaluate at least two viable AMD-compatible runtimes or backends.
- Add local document extraction, indexing, retrieval, and citations to source passages. Start with bounded lexical search; choose a local embedding model after runtime/hardware evaluation.
- Use synthetic documents for automated and cloud tests.

Exit evidence: an end-to-end local chat and document Q&A demo that works without internet access after setup.

Current status: the software-in-loop implementation is in `assistant/`. Deterministic tests exercise direct answering, manager-to-specialist document search, citations, upload/removal, local-origin protections, and bounded PDF expansion. It has not yet been run with real model weights, so offline model quality and latency are unverified. The index uses lexical FTS5 search; semantic embeddings, comparison with a second AMD-compatible runtime, and target-hardware measurements remain unfinished.

## Milestone 4: Target appliance validation
- Install the chosen Linux version on the selected EVO-X3 unit.
- Verify Wi-Fi access-point mode, Secure Boot configuration, and power restoration.
- Benchmark approximately 14B, 30B, 70B, and 100B/MoE model classes at documented quantizations.
- Measure memory use, response speed, power, thermal behavior, and noise under sustained load.

Exit evidence: a reproducible benchmark report and a justified default-model recommendation.

## Milestone 5: MVP hardening and limited alpha
- Add trusted-device management, storage protection, signed updates, rollback, and recovery UX.
- Test interrupted setup, network loss, power cycling, malformed uploads, and device reset.
- Complete an independent security review and fix high-severity findings.
- Run usability sessions with non-technical users.

Exit evidence: an alpha release with recovery instructions, known limitations, and no unsupported privacy or security claims.

## Later work
Evaluate remote access, multi-user support, fleet management, and manufacturing only after the local-network MVP succeeds.
