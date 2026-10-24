# Project working rules

## Mission
Build a local-first home AI appliance that is approachable for non-technical users. The current MVP goals and acceptance criteria are in docs/PROJECT_BRIEF.md; the delivery sequence is in docs/ROADMAP.md.

## How to work
- Inspect the brief, roadmap, current repository state, and relevant issues before changing files.
- Choose sensible, reversible implementation details without asking for routine decisions. Record decisions that affect architecture, privacy, security, supported hardware, or user experience in docs/DECISIONS.md.
- Work milestone by milestone. Keep changes focused, explain what changed, and open a pull request for each meaningful milestone.
- Use subagents for independent UX, Linux networking, inference, and security/quality work when that speeds up the result. The lead agent owns integration and final review.
- Continue to the next planned task after reporting a milestone. Ask only when blocked by missing account access, physical hardware or phone testing, a decision that materially affects user data or security, paid cloud spending, or an irreversible action.
- Never merge a pull request, publish a release, deploy externally, change repository visibility, or incur cloud charges without the owner's explicit approval.
- Run checks appropriate to the change and state exactly which checks ran. Do not imply unrun checks passed.

## Product and privacy constraints
- Local processing and local-network access are the MVP default. Do not add mandatory cloud accounts, cloud inference, telemetry, or external data transfer without documenting the reason and getting approval.
- Never commit credentials, private documents, home-network details, or real user data. Use synthetic documents for development and cloud testing.
- Generate appliance identity during customer setup. A new trusted device must require a physical authorization action.
- Use established, reviewed cryptographic and networking components. Do not invent a custom cryptographic protocol.
- Treat security properties as design goals until tested and independently reviewed. Do not call the appliance unhackable or production-ready.
- The repository includes CC0 1.0 Universal in LICENSE. Review the license of every code dependency, model artifact, and dataset separately.
- Keep prototype behavior and security properties clearly labeled; never make a simulated action appear to control hardware.

## Hardware and evidence
- Distinguish laptop simulation, cloud capacity experiments, and tests on the target appliance.
- For hardware results, record the exact device, operating system, kernel/runtime versions, model and quantization, context length, test method, and measurements.
- Do not treat model size or memory fit as proof of acceptable response speed or answer quality.

