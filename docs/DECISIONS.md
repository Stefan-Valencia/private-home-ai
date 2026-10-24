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

