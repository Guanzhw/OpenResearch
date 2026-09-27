# Source audit after blind preference

First record the user's initial A/B/tie/cannot-judge impression and reason in `review.md`. Then use this sheet to check the strongest factual claims in each report while labels remain blind. The reviewer should inspect 3–5 consequential claims per full report, including surprising numbers or causal attributions, and record the exact sentence, original-source location, and judgment. A missing citation is a traceability problem; an unsupported or contradicted claim is a factual problem. Do not infer quality from citation count alone. Ask the user for a final choice after this audit and before revealing the A/B key.

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

## `driving-end-to-end-history`

This confirmation case has no fixed answer outline. The reviewer should check selected original papers for chronology, claimed problem/solution links, evaluation setting, and the limits of each route. Add source anchors only **after** the candidate has been selected; if anchors become new scoring rules, start a new round and rerun the control.
