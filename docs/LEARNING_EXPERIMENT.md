# Learning experiment for manual revisions

## Question

Can the assistant recognize that its document answers confuse revisions, select a permitted retrieval change, and show on new examples that the change improves its answers? The owner asks for better answers about which instructions are in effect and authorizes a local experiment on synthetic manuals.

## Baseline and candidate

Freeze the current SQLite FTS5 retrieval configuration as the baseline. Use the four `manual_` cases in the [software evaluator](../assistant/home_ai/evaluate.py) as visible development examples. Let the assistant inspect those manuals and its development results. Ask it to describe the gap, predict how a change would help, and select one option from a small set of reviewed retrieval configurations. Example options are the baseline ranking and a ranking that considers explicit approval status for current-revision questions while still showing competing evidence. A newer date alone is insufficient evidence of approval.

Record the proposal and freeze one candidate before scoring. For both runs, use the same corpus, answer prompt, model and runtime settings, retrieval limit, and budget. Allow one candidate trial per held-out set. Fix time and request limits before running, and record any timeouts. Use isolated local indexes with synthetic inputs. Limit the assistant to the approved evaluation configurations and authorized input collection. Keep the normal assistant available.

## Independent evaluation

Have a separate reviewer prepare and keep the held-out prompts, expected evidence, and scoring rubric outside the proposal workflow. Freeze those materials before seeing the candidate. Use invented equipment and revision records distinct from the development fixtures, including overlapping wording and misleading dates. Provide the synthetic source corpus to each evaluation run, with the prompts withheld until scoring and the answer key available only to the reviewer.

Use 16 paired cases, with four in each group.

| Case | Evidence required |
| --- | --- |
| Current instructions | Cite the approved revision and attribute the value correctly, including a case with a newer draft. |
| Historical comparison | Report each value and tie it to the correct revision and citation. |
| Unresolved conflict | Cite the disagreement and say that the authoritative instruction cannot be determined. |
| Missing information | Say that the supplied materials do not establish the requested detail. |

Present answers to the reviewer in mixed order with configuration names hidden. Score each case pass or fail against the rubric. A passing answer needs the right conclusion, correct revision attribution and supporting citations for material claims, and appropriate uncertainty. Check source coverage at rank five separately to diagnose retrieval misses. Run the existing synthetic suite with both configurations to catch regressions outside the revision cases.

As a pilot gate, require at least two additional held-out passes, zero previously passing cases turning into failures across both sets, and zero unsupported claims about which revision is authoritative. If the baseline leaves fewer than two possible gains, record a ceiling result and design a harder set before another trial. Report raw paired counts and treat the small sample as an initial signal.

## Replay, model trial, and rollback

A deterministic replay on a development machine can exercise the existing lexical baseline and, once a candidate configuration is implemented, verify ranking, scoring inputs, isolation, and rollback. Scripted candidate selection and scripted answers establish workflow behavior only. A separate trial with a suitable local model must record the model identifying the gap and selecting the candidate from development evidence, then score its generated answers on the held-out set. Record target appliance performance in a separate hardware session.

Keep the baseline configuration and index available throughout. Record the run ID, corpus and configuration versions, selected change and rationale, limits, scores, and decision. Keep the candidate isolated if it fails a gate, exceeds its budget, or lacks sufficient evidence. A human reviewer decides whether to adopt a passing candidate, with a documented way to restore the previous configuration and verify that it is active.
