# Source audit after blind first impression

For field reports, first record the user's initial A/B/tie/cannot-judge impression and reason in `review.md`. Then use this sheet to check factual claims while labels remain blind. For source-check cases, check every frozen reviewer-only `grading.required_facts` item and `grading.critical_errors` entry in `cases.json`, then audit other consequential claims against primary sources. For field reports, inspect 3–5 consequential claims, including surprising numbers or causal attributions. Record the exact sentence, original-source location, and judgment. A missing citation is a traceability problem; an absent required fact is missing; a contradicted or misstated claim is wrong. Do not infer quality from citation count alone. The frozen factual pass/fail is the primary source-check outcome; user preference is optional and separate. For field reports, the user's final blind preference is primary. Record outcomes after the audit and before revealing the A/B key.

## `embodied-transformer-history`

Check whether the report explains *why* major approaches followed one another, names representative primary work, and distinguishes paper claims from the report's synthesis. Inspect at least one pivotal transition and one quantitative claim against the original paper. The user decides which report better builds an understanding of the field.

## `pi0-latency`

Original source: [π0 paper, Appendix D, Table I](https://arxiv.org/html/2410.24164).

- On an NVIDIA GeForce RTX 4090 with three camera images, the paper reports 14 ms for image encoders, 32 ms for the observation forward pass, and **27 ms for ten action/flow forward passes together**.
- The total is 73 ms on board, or 86 ms off board including 13 ms of network latency. A report that calls 27 ms the total robot-side latency misreads the table.
- The paper reports executing action chunks between inferences; a claim about closed-loop rate needs to account for that operating mode and hardware setting.

## `virtualhome-attribution`

Original source: [Huang et al., Sections 3.2–3.4 and Tables 1–2](https://arxiv.org/html/2201.07207).

- In Table 1, Vanilla Codex 12B has 18.07% executability and the complete Translated Codex 12B method has 78.57%. That is a **complete-method comparison**, not an isolated estimate of action translation.
- Table 2 ablates three components: without action translation 31.49%, without dynamic example 50.86%, and without trajectory correction 55.19% executability, against 78.57% for the full method. Translation has the largest ablation effect among these, while the other components also contribute.
- Correctness and executability differ. Table 1 reports 64.87% correctness for Vanilla Codex 12B and 54.88% for the translated version; a report should not turn improved executability into an unqualified overall improvement.

## `molmoact-action-representation`

Sources: [MolmoAct, Section 2.3](https://arxiv.org/html/2508.07917); [Action Hallucination, Section 1](https://arxiv.org/html/2602.06339).

- MolmoAct describes autoregressive action tokens in Section 2.3. Check that the report verifies and names this architecture against the original paper.
- Action Hallucination places MolmoAct among conditional flow/diffusion examples in Section 1. Compare that characterization directly with MolmoAct and require the report to state the discrepancy.
- A general account of action-model families does not resolve this claim; the report should identify MolmoAct and cite both source locations.

## `embodied-closed-loop-history`

Sources: [RT-1](https://arxiv.org/html/2212.06817); [RT-2](https://arxiv.org/html/2307.15818); [Embodied-R1.5](https://arxiv.org/html/2606.11324).

- Check RT-1 and RT-2 for pre-2025 low-level robot control that repeatedly uses observations to produce actions. The report should not date the beginning of closed-loop robot control to 2025–26.
- Check Embodied-R1.5 for task-level planning, monitoring, and replanning. Distinguish this reasoning loop from the earlier perception-to-action control loop and state which level any novelty claim concerns.
- Require source locations for each paper used to establish the chronology and the distinction between control levels.

## `adamw-decoupled-weight-decay`

Original source: [Loshchilov & Hutter, Decoupled Weight Decay Regularization](https://arxiv.org/html/1711.05101v3).

- Section 2, Proposition 1, shows standard SGD equivalence only with coefficient rescaling by the learning rate (`lambda-prime = lambda / alpha`). Proposition 2 establishes that this equivalence fails for adaptive gradients such as Adam.
- AdamW applies weight decay separately from the adaptive gradient update. With L2 regularization in Adam, the regularizer's gradient is scaled as part of the adaptive update.
- The paper's main generalization comparisons are on image-classification datasets, including CIFAR-10 and ImageNet32x32. Section 5 says the results need verification on a wider range of tasks; do not turn these experiments into a universal optimizer ranking.

## `sqlite-wal-concurrency`

Original source: [SQLite Write-Ahead Logging](https://www.sqlite.org/wal.html).

- Sections 1 and 2.2 say readers and a writer can usually proceed concurrently, but only one writer can write at a time. Section 9 documents cases where queries return `SQLITE_BUSY`.
- Sections 2.2 and 6 explain that a long-running reader can stop checkpoint progress. The WAL can be reset only after all content is checkpointed and synced and no reader still uses the WAL, so a long reader can delay reset.
- Sections 1 and 2.2 explain that WAL uses shared memory among processes on the same host and does not work over a network filesystem.

## `driving-end-to-end-history`

This confirmation case has no fixed answer outline. The reviewer should check selected original papers for chronology, claimed problem/solution links, evaluation setting, and the limits of each route. Add source anchors only **after** the candidate has been selected; if anchors become new scoring rules, start a new round and rerun the control.
