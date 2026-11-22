# First hardware validation session

Use this runbook to gather the first Linux and appliance evidence for the [MVP test plan](TEST_PLAN.md). Record each result against the machine and software actually used. A spare Linux PC is enough to start. Repeat checks that depend on the Wi-Fi adapter, firmware, power behavior, or AMD inference backend on the target appliance.

## Prepare the bench

- Use a spare machine, an isolated test router or network, a local console, and synthetic documents. Have a phone for the setup flow and a second test client for device removal once those features exist. Keep a recovery boot medium and a backup handy before changes to disks or firmware.
- Stage the project, Python environment, inference runtime, and a permitted small model artifact before disconnecting internet access. Record the model revision, quantization, and artifact hash. Start with one runtime and model you can run comfortably. Use the install and loopback startup steps in the [assistant README](../assistant/README.md).
- Put prototype uploads in a fresh disposable directory using `HOME_AI_DATA_DIR`. Use test network credentials and keep them out of command output, screenshots, and the evidence log. Redact serial numbers, account paths, private network names and addresses, and any secrets before sharing results.
- Label the session **Spare Linux PC**, **Target appliance**, or **Simulation**. Record the Git revision and any local edits needed to reproduce the run. Mark each check **Pass**, **Fail**, **Blocked**, or **Skipped**, with a reason and concrete evidence. Reserve **Pass** for the specific behavior observed.

## 1. Establish the Linux baseline

| Check | Procedure | Evidence to capture |
| --- | --- | --- |
| Boot and storage | Boot the selected Linux image, verify the local console and expected storage, and perform a normal reboot. Use a spare disk if installation could affect an existing system. | Exact hardware and Linux image, kernel, firmware, detected storage and memory, and reboot result. |
| Firmware | Record the Secure Boot state and whether Linux boots with the intended firmware settings. Record the configured response to AC restoration where available. | Firmware version, boot mode and Secure Boot state, AC restore setting, and any changes. |
| Wi-Fi feasibility | Identify the adapter and driver. Verify client mode on the test network. Using the selected Linux network tooling, create a temporary lab access point and confirm a phone can join it and load a local test page. Stop the access point and confirm it disappears. | Adapter, driver, firmware, access point and client mode results, phone OS/browser, and time to reconnect. Record whether both modes can run together if the tested design needs that. |
| Power restoration | On the disposable bench system, observe behavior after a normal shutdown followed by AC removal and restoration. Once recovery is ready, run a separate approved power loss trial during setup with test data. | Whether the machine boots independently, time to availability, network and application state, and any manual recovery steps. |

This phase can show adapter and platform feasibility with a test page. Run customer onboarding evidence in phase 3 when the real provisioning path is available.

## 2. Prove local AI on Linux

1. Start the assistant and inference server on IP loopback. Open the assistant from the Linux machine itself. Record the listening interfaces and confirm the prototype services stay on loopback. Phone access to the assistant requires the reviewed trusted device implementation.
2. Leave the local bench network up and remove its internet uplink. If the test machine has another uplink, disconnect it as well. Verify the loss of internet through the bench setup. From a cold service start, ask one general question, then upload a synthetic text file and a synthetic selectable text PDF. Ask questions with known answers and confirm each citation points to the correct source and page.
3. Ask an unsupported question and record whether the assistant acknowledges missing evidence. Remove a fixture and verify a new conversation cannot retrieve it. Record only the observed deletion behavior in the application and clarify any separate storage checks.
4. Stop the model server and send another request. Expect an unavailable message and verify the app can answer locally again after the model restarts. Record how the endpoint and network observations were checked. A successful offline demo establishes independence from internet access in that configuration. Claims about outbound traffic also need observations during connected use.
5. From `assistant/`, run `python -m home_ai.evaluate --retrieval-only` and `python -m home_ai.evaluate` with the selected local model running for the second command. Keep the sanitized output with the session record. Record the number of cases, retrieval recall, routing and citation metrics, abstention, tool argument validity, synthetic canary results, and latency. Assess model quality separately from platform feasibility and share any incomplete measurements explicitly. See the [model evaluation plan](AGENT_MODEL_EVALUATION.md) for quality gates.

## 3. Validate onboarding and recovery when implemented

Use a real provisioning build for first boot and network recovery. Run trusted device checks after the protocol, transport, credential storage, and recovery design have been selected and reviewed. Follow the [pairing threat model](THREAT_MODEL.md) when deciding which checks the implementation can satisfy.

| Check | Procedure | Expected observation |
| --- | --- | --- |
| First boot | Start from documented uninitialized state. On a representative phone, find the setup access point, open the setup page, and connect the appliance to the test Wi-Fi. Repeat with a second representative phone/browser as available. | Setup completes through the intended path, the temporary access point closes, and the phone can reach the normal service through the approved flow. Record duration and any manual workarounds. |
| Setup failures | Use invalid test credentials, remove the test router briefly, and interrupt setup at documented checkpoints. Restore the network and retry. | The user sees a clear error and can retry or recover. After a configured reboot the appliance reconnects without leaving the temporary access point open indefinitely. |
| Physical pairing | Confirm a fresh appliance identity is created at initialization. With the approved flow, check that enrollment is unavailable before a physical action, works inside the authorization window, and becomes unavailable at the end of that window. | Record identity freshness without private keys, the observable state and timings, and successful device-key access without a conventional username/password account. |
| Removal and reset | Remove a second enrolled test device and check its next normal request. From a disposable instance, exercise owner recovery and reset using the documented steps. | The removed device loses protected access and the owner can recover without undocumented workarounds. Record which trust records and test data are retained or removed, according to the approved policy. |

## 4. Benchmark on the target appliance

1. Start with one known working model. Confirm the runtime is using the intended backend and record any CPU fallback. Compare two viable backends with the same model artifact, quantization, context, prompt set, and concurrency where possible. If a backend needs different artifacts, report the comparison as two complete configurations and record the differences.
2. For cold starts, record model load time separately. For warm runs, use identical synthetic prompts, context size, output budget, and generation settings. Record the warm-up policy and sample count. Measure time to first token at a streaming runtime interface if available, prompt processing and generation tokens per second, and end-to-end response time through the app. Record the measurement point for each figure.
3. Repeat under a sustained workload with a fixed duration and request cadence. Log idle and loaded power if a meter is available, temperature, fan or noise observations, memory use, and throughput at the beginning and end. Record how readings were taken, particularly whether memory is system-wide or process-reported and whether power is measured at the wall. Treat missing sensors as unmeasured.
4. Expand the matrix to model classes in the [roadmap](ROADMAP.md) after the initial configuration is stable. Report model load failures, out-of-memory events, CPU fallback, and performance degradation alongside successes. Recommend a default only from measured quality, response time, and sustained behavior. Reuse the evaluation settings and evidence format when comparing candidates.

## Session record

Copy this template per machine and run. Attach only sanitized device output, evaluator summaries, or aggregate metrics.

```text
Date and duration:
Environment (spare Linux PC / target appliance / simulation):
Device, CPU/GPU, RAM, storage, Wi-Fi adapter:
Firmware, Secure Boot, memory allocation and power settings:
OS image, kernel, driver and relevant package versions:
Project revision and local edits:
Test router/client/browser (sanitized):
Runtime version/build, backend and offload:
Model source/revision/license/hash, quantization:
Context, output budget, generation settings, concurrency:
Prompt set revision, warm-up, sample count, sustained duration:
Check | expected result | observed result | status | evidence
Measurements with units and collection method:
Evaluation metrics, incomplete metrics, and limitations:
Decision or next test supported by this evidence:
```

The first spare PC session should leave a reproducible Linux and offline inference record plus a list of gated setup checks. Target appliance validation adds repeatable hardware results and enough comparable model evidence to choose a default. Hardware findings do not replace the independent security and recovery checks required for alpha.
