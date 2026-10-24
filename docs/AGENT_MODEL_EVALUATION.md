# Home AI agent and model evaluation plan

**Status:** Proposed software plan. Runtime and default model remain open until measured on the target appliance.

## Product behavior

The user should be able to enter one plain-language request. The assistant should decide whether to answer directly, search local material, call an allowed tool, or delegate a bounded task to a specialist. It should not ask the user to choose agents, tools, or model settings.

For the first implementation:

- Keep the orchestrator and model behind a replaceable provider interface.
- Give the orchestrator a fixed registry of narrowly scoped tools and named agents. It may choose among them, but cannot create new tools, call arbitrary network services, or run a shell.
- Start with local document search and simulated home status as read-only tools. Do not connect real devices or perform state-changing home actions in this slice.
- Treat uploaded documents and tool results as untrusted content, not as instructions to the assistant.
- Keep prompts, documents, retrieval indexes, and inference on the appliance by default. Do not add telemetry or a cloud model fallback.
- Require an application policy check before every tool call. A future device-control capability must have its own authorization and confirmation design before implementation.

This gives the user a single prompt while keeping permissions in application code instead of relying on a model to police itself.

## Harness recommendation

Prototype **Pydantic AI** as the general-purpose orchestrator. Its subagent capability exposes a named `delegate_task(agent_name, task)` tool, forwards dependencies and usage limits, and gives each delegate an isolated run history. That fits the product goal of letting the assistant decide when delegation helps without exposing setup choices to the user. [Pydantic AI multi-agent guide](https://pydantic.dev/docs/ai/guides/multi-agent-applications/)

Keep the first graph small: one manager, a local knowledge agent, and a simulated home-information agent. The manager can answer directly when delegation adds no value. Add a bounded task limit and a per-request tool-call limit to prevent loops.

Compare **Qwen-Agent** as a reference implementation when evaluating Qwen models. Qwen recommends it for Qwen3.6 agent applications, and it supports tools and MCP; its model-specific convenience is a reason to compare it, not enough by itself to select it for the product. [Qwen3.6 agentic usage](https://huggingface.co/Qwen/Qwen3.6-35B-A3B#agentic-usage), [Qwen-Agent repository](https://github.com/QwenLM/Qwen-Agent)

Keep **LangGraph** as a later option if the product needs durable, resumable workflows or explicit long-running state. Its router pattern supports directing a request to one or more specialized agents and synthesizing their results, but the initial MVP does not need a graph unless measurements reveal a concrete need. [LangChain router guide](https://docs.langchain.com/oss/python/langchain/multi-agent/router)

## Model and inference candidates

Start with a deterministic fake provider for repeatable offline development. Add a local model behind an OpenAI-compatible API so the agent code does not depend on one inference engine. `llama.cpp` provides CPU and GPU inference, chat and embeddings endpoints, and tool-calling support; use it as the laptop software-in-loop candidate, not as proof of AMD target performance. [llama.cpp server guide](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)

Evaluate these open-weight candidates:

1. **Qwen3.6-35B-A3B** — the first model to try for the target class. Its card lists 35B total and 3B active parameters, Apache-2.0, tool-use serving guidance, and a native 262K context. Its card recommends Qwen-Agent for agent applications. These are model-card facts and vendor recommendations, not independent quality or speed results. [Model card](https://huggingface.co/Qwen/Qwen3.6-35B-A3B)
2. **OpenAI gpt-oss-20b** — a smaller local comparison for latency and resource use.
3. **OpenAI gpt-oss-120b** — a higher-capacity comparison. Its card lists 117B total and 5.1B active parameters, Apache-2.0, and native function-calling capability. The card's single 80GB GPU statement does not establish that it will fit or perform acceptably in an integrated-memory appliance. [Model card](https://huggingface.co/openai/gpt-oss-120b)

Model size alone is not a selection criterion. Quantization, context size, runtime support, prompt format, tool-call reliability, answer quality, memory use, and sustained speed all need measurement. Review the license of the actual quantized artifact and its conversion separately before redistribution.

## Evaluation plan

Create a fixed synthetic set of 20–30 documents and 40–50 requests. Include direct questions, paraphrases, questions spanning multiple documents, unsupported questions, ambiguous requests, prompt-injection text embedded in documents, and requests that should not invoke a tool.

Compare harness/model pairs on:

- Whether the assistant chooses direct response, local retrieval, a tool, or delegation appropriately.
- Tool selection and schema-valid arguments, including avoiding unnecessary calls.
- Answer support and citation correctness for document questions.
- Correct abstention when local evidence is missing.
- Resistance to instructions embedded in retrieved content.
- Median and tail response time, peak memory, and stability under a fixed context and request limit.

Use a deterministic provider for app and policy tests. Use the same synthetic prompts and tool permissions for each local model. Record harness version, model revision, quantization, runtime, context, hardware, and all measurements. Do not present vendor benchmarks as our own results or set a default based only on parameter count.

## Software-in-loop path without physical devices

Continue with the browser onboarding simulation and add an isolated Linux VM or network-namespace setup service with mocked access-point and NetworkManager events. Exercise DHCP/DNS, setup-page reachability, wrong-password, router-unavailable, restart, and reset paths using synthetic state. Run responsive-browser automation at phone-sized viewports.

This can validate service logic, state transitions, and browser behavior. It cannot verify radio coverage, access-point compatibility, real phone captive-portal behavior, or appliance recovery under power loss. Keep those items in Milestones 1 and 4 for the target device.

## Effort and expected result

The AI software slice is estimated at **4–6 engineering days** after the onboarding prototype:

- 1–2 days: provider interface, manager, bounded delegation, and policy-checked simulated tools.
- 2–3 days: text/PDF ingestion, local retrieval, citations, and clear unsupported-content behavior.
- 1–2 days: synthetic evaluation set, harness comparison, quality report, and review.

Expected result: a local chat demo that accepts one user prompt, decides whether to answer or use a permitted local capability, can delegate when helpful, answers synthetic document questions with citations, and abstains when evidence is missing. This does not include actual home-device control or target-hardware performance claims.

Target-appliance setup, AMD runtime comparison, memory/speed/thermal measurements, and radio/phone tests remain separate work after the hardware is available.
