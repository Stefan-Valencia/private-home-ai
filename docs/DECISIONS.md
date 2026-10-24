# Decision Log

Record decisions that affect architecture, privacy, security, hardware, or user experience. Include date, decision, reasoning, and revisit conditions.

## Initial direction

### Local-first MVP
Status: accepted as the MVP baseline.

The appliance should run inference and process documents locally by default. Remote access and cloud inference are deferred.

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
