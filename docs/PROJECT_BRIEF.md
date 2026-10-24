# Private Home AI Appliance: Project Brief

## Product goal
Make a private local AI computer feel as easy to set up as a home router. The appliance stays in the home, serves a browser interface to trusted devices, and processes models and documents locally by default.

## MVP user journey
1. The customer powers on an uninitialized appliance.
2. The appliance provides a temporary setup Wi-Fi network.
3. The customer connects a phone and opens a local setup page.
4. The appliance creates a fresh device identity during customer setup.
5. The customer physically authorizes pairing of the first trusted device.
6. The customer selects the home Wi-Fi network and credentials.
7. The appliance joins the home network and closes or disables setup mode.
8. The customer opens a browser interface from the trusted phone or computer.
9. The customer chats with a local model and can upload documents for local question answering.
10. The customer can pair and remove additional trusted devices.

## MVP requirements
- Phone-friendly first-boot setup on a local network.
- Fresh appliance identity created at customer initialization.
- Physical authorization for adding a trusted device.
- Home Wi-Fi provisioning and recovery after restart or loss of power.
- Browser-based chat using a local inference runtime.
- Local document ingestion, retrieval, and question answering.
- Basic trusted-device management and clear privacy status.
- No mandatory cloud account, cloud inference, or remote access in the baseline MVP.

## Security and privacy goals
- Require physical access to authorize a new trusted device.
- Use short-lived pairing material and reviewed cryptographic/networking components.
- Keep user documents, prompts, embeddings, and device secrets on the appliance by default.
- Explain the limits of supply-chain and physical-tampering protections honestly.
- Design encrypted storage, signed updates, rollback, and recovery before calling the product production-ready.
- Threat-model pairing, first boot, local-network access, device loss, updates, recovery, and physical access before making security claims.

## Working architecture proposal
- Ubuntu Linux on the first prototype, subject to validation on the exact hardware.
- Standard Linux networking components for access-point mode and home Wi-Fi provisioning.
- A local web setup application and browser AI interface.
- An isolated service for local inference; evaluate AMD-compatible runtimes and backends on the target device.
- Local document extraction, embeddings, and retrieval.
- Signed software updates and a tested recovery path before product release.

These are starting points, not locked decisions. Record changes in docs/DECISIONS.md.

## Prototype hardware
The current evaluation target is a compact system using AMD Ryzen AI Max+ 395, Radeon 8060S graphics, and 128 GB of shared unified memory, with 2-4 TB NVMe storage. The target is a test candidate, not a final product commitment. Linux support, access-point behavior, inference speed, sustained thermals, noise, power use, storage, and recovery all require direct validation.

## Model evaluation
Compare several model sizes and quantizations on the target system. Measure model fit, memory use, time to first token, generation speed, context length, answer quality on a fixed task set, power, and sustained thermal behavior. A model that fits memory is not automatically fast or suitable for the product.

## Deferred scope
- Secure remote access from outside the home.
- Cloud inference or cloud accounts.
- Enterprise multi-user roles and fleet management.
- Custom motherboard or custom CPU/GPU design.
- Production manufacturing and large-scale support operations.

## Open decisions
- Default model and fallback model.
- Inference runtime and AMD backend.
- Pairing protocol and independent security review.
- Storage encryption and recovery experience.
- Update mechanism, signing keys, and rollback design.
- Model-artifact and dataset distribution terms.

