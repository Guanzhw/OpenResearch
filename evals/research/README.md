# Research report evaluation set (v0.3.0)

This set evaluates OpenResearch's field-learning workflow on source-grounded questions and field reports. The primary outcome depends on the case kind: source-check cases use the frozen factual rubric; field-report cases use the user's blind preference. Record style, holistic usefulness, source-audit findings, and run cost separately.

`cases.json` v0.3.0 freezes eight tasks: two qualitative field reports and six source checks on π0 latency, VirtualHome attribution, MolmoAct's action representation, closed-loop robot control, AdamW weight decay, and SQLite WAL concurrency. AdamW and SQLite ask for short reports so factual scoring can be applied to a reader-facing artifact. Round 003 remains tied to its frozen v0.1.0 casebook snapshot and manifest; neither is changed by this update. Keep each case's prompt and review criteria fixed within a comparison round; if they change, version the round and rerun its control.

## Set up a real paired run

1. **Choose the question and intervention before generating reports.** Run one fresh OpenResearch session per arm. Send the exact `prompt` from `cases.json` to each. The control and treatment should use builds from one common codebase that differ only in the field-learning instructions being tested. Save the actual loaded instruction files and the **effective expanded prompt** for each arm. The short slash text in the chat history is insufficient because OpenResearch expands slash workflows before sending them to the harness. `init` saves a casebook snapshot beside the manifest so later additions to the suite do not change this round.
2. **Match the environment.** Use the same harness, model, effort, enabled tools, source access, neutral model-visible project name, empty starting project, wall-time limit, tool-call limit, and token ceiling. Give each arm a unique opaque filesystem path that does not reveal its arm or workflow condition. Keep the arm mapping in the manifest and reviewer key; developer instructions visible to either run must not reveal control/treatment or the workflow condition. Round 003 exposed that mapping in developer instructions, so future runs use this masking rule. Use one attempt per arm per pair and count timeouts and failures. Do not select the best attempt after seeing results. Record the build commit or complete source-snapshot hash and inspect the code diff to confirm the intended instruction change is the only difference.
3. **Preserve evidence.** Save the full agent trace, report, loaded instruction snapshots, effective prompt, status, elapsed time, tool calls, and cumulative input/cached-input/output tokens. A missing value is `null` with an explicit reason. `used_tokens` is context occupancy, not cumulative spend. Include subagent and automatic-review usage when available; otherwise state the measurement gap. Store run artifacts outside the public repository unless the user elects to publish them.
4. **Blind the review.** Fill the manifest created below, validate it, then create an A/B packet. Keep the identity key outside the reviewer directory. The tool hides the arm labels and copies linked local files under `A/` and `B/`; inspect the reports and assets for identifying text or paths before calling the review blind. If an arm is recognizable, record the review as unblinded. For a field report, ask the user for a first impression before showing `source-audit.md`, then record the user's final A, B, tie, or cannot-judge choice before opening the identity key. For a source check, have the reviewer score the frozen facts while labels remain hidden; user preference is optional and separate. Keep all attempts in the comparison ledger, including incomplete ones.

The current built-in `orx-lit-review` skill already matches field-learning questions. Plain text versus `/learn-field` on the same current build tests the value of the explicit shortcut, **not** the full workflow's presence. For the full with/without question, build a controlled instruction ablation. Comparing the pre-integration build with the current branch without checking their full diff would include other changes. Built-in skills are compiled into the binary and refreshed into sessions, so editing a session's skill file does not create a controlled arm.

## Factual scoring for source-check cases

Each v0.3.0 source-check case has a frozen `grading` object in `cases.json` for reviewers. Keep those reviewer-only keys out of candidate prompts and loaded skill files. A factual pass requires support for every `required_facts` item and no `critical_errors`. Mark an absent fact as **missing** and a contradicted or misstated fact as **wrong**. Check other consequential factual claims against primary sources and record them too. Score style and holistic usefulness separately. The two field-report cases remain qualitative and use blind user preference as the main outcome.

## Commands

Requires Python 3 and no extra packages. These commands only prepare and inspect files; they never launch a model.

```powershell
python evals/research/eval.py validate
python evals/research/eval.py init embodied-transformer-history D:/Caches/OpenResearch/evals/round-001/manifest.json
# Fill the manifest before the two runs; replace pending fields with recorded values afterward.
python evals/research/eval.py validate --manifest D:/Caches/OpenResearch/evals/round-001/manifest.json
python evals/research/eval.py packet D:/Caches/OpenResearch/evals/round-001/manifest.json D:/Caches/OpenResearch/evals/round-001/reviewer D:/Caches/OpenResearch/evals/round-001/identity.json
```

The manifest has one `shared` configuration and two `arms`. `workflow_files` are copies of instructions actually loaded by each run. `effective_prompt_file` contains what the harness received, including expansion and injected instructions. `trace_file` is the full transcript/log. A complete run needs a nonempty `report_file`; a failed or timed-out run needs `failure_reason`. The packet generator checks file presence, copies simple relative Markdown and HTML linked files while preserving their paths, and hashes the artifacts. If a local link cannot be packaged, it stops so the reviewer does not see broken evidence. **Validation establishes record completeness, not that the declared environment actually matched**; verify that against the traces and build diff.

For existing reports without full run provenance, use `preview` to check the review surface. It labels the packet as an archive preview and cannot establish an effect:

```powershell
python evals/research/eval.py preview embodied-transformer-history report-1.md report-2.md D:/Caches/OpenResearch/evals/preview/reviewer D:/Caches/OpenResearch/evals/preview/identity.json
```

## Decision record

Record one row per paired case: case ID and suite version; control/treatment build and workflow hashes; status of both attempts; the source-check factual verdict or field-report final blind choice; any separate user preference and its reason; source-audit findings; total elapsed, tool calls, and cumulative tokens per arm; protocol deviations; and the decision to keep, revise, or discard the change. Report the results case by case. A single pair is exploratory evidence, not an estimate of general performance. Avoid tuning against the confirmation case; run it after selecting a candidate with the same frozen evaluator.

This protocol follows the task/trace/grader separation in [Anthropic's agent-eval guide](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents), with the user as the primary grader for usefulness.
