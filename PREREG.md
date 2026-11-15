# Pre-registration

This file fixes the claims, comparisons, metrics and pass criteria before any confirmation data is labeled or evaluated. Numeric settings live in `config.yaml`. Any change to either file after the confirmation labels exist is logged at the bottom with a reason.

## Claims

- **H1a (admission).** At a matched wrong-reuse rate, a cache admission policy that uses mined behavioral patterns serves more requests from cache than the per-query policies below.
- **H1b (routing).** At a matched cost, a router that uses mined behavioral patterns reaches higher answer quality than per-query routers.
- **H2 (stretch, exploratory).** Fast-tracking mined successful trajectories reduces turns to a satisfactory answer without raising the failure rate. It is reported as exploratory; no confirmatory claim is made.

## Definitions

- **Turn:** one user request plus the assistant answer that followed it.
- **Entity:** a session (one conversation) or a user (hashed identifier).
- **Behavioral pattern:** a frequent itemset (FP-Growth) or frequent ordered sequence (PrefixSpan) over the `(intent, dialogue act)` tokens of an entity's past turns. Patterns are mined only from turns that happened before the decision being made.
- **Candidate:** one of the top-K most similar earlier turns, by cosine similarity of the request embeddings, at or above the similarity floor.
- **Acceptable reuse:** an LLM judge, shown the new request, the answer actually given to it (the reference), and the candidate's answer, says the candidate's answer would serve the new request. The judge is validated against two human raters on the gold set, and must reach the agreement gate before its labels are used.
- **Hit rate:** the share of all requests in the evaluation period served from cache.
- **Wrong-reuse rate:** the share of served requests whose served answer is not acceptable.

## Comparators (admission)

| Policy | Decision signal |
|---|---|
| P1 | fixed cosine threshold on the top candidate |
| P2 | per-intent cosine thresholds, fit on the training period |
| P3 | learned per-query verifier: similarities, current intent and act, lengths, time gap |
| P5 | P3 plus an embedding of the session's previous turns (context-aware, no mining) |
| P4 | P3 plus mined pattern priors and pattern features |
| P4+ | P5 plus mined pattern priors and pattern features |

P4 vs P3 isolates the contribution of patterns. P4+ vs P5 tests whether patterns add value beyond raw conversation context.

## Data and splits

- **Source:** WildChat-1M English multi-turn conversations, streamed in dataset order.
- **Split by time:** sessions go to train, dev or confirm by the time of their first turn (60/20/20).
- **Development:** all feature and model iteration happens on train and dev.
- **Confirmation:** the confirmation period is evaluated once, with frozen code (a git tag).

## Primary test (H1a)

- **Metric:** hit rate at wrong-reuse of at most 5% and at most 10%, read from each policy's curve over the confirmation period.
- **Uncertainty:** 95% session-bootstrap CI of the paired difference, P4 minus each comparator, with Holm correction across the two levels.
- **Pass:** H1a passes if P4 beats the best of P1, P2, P3 and P5 at both levels with the corrected CI excluding zero.
- **Reporting:** results are reported whatever they show.

## Supporting analyses, fixed in advance

- **Placebos:** the same P4 pipeline with (a) each session's history shuffled in time, and (b) each request given a random other session's history. A real pattern effect should disappear in both.
- **Positive control:** a semi-synthetic set with injected context-dependent duplicates, where the right decision is known.
- **Mechanism:** the gain broken down by dialogue act and turn position. Patterns are expected to help most on follow-ups and corrections and least on first turns.
- **Ablations:** frequent-only, sequential-only and both; session-scoped vs user-scoped patterns; feature importance.
- **Robustness:** a second embedding model, a second judge on the gold set, and a different similarity floor.

## Routing (H1b)

- **Data:** human pairwise votes between models on multi-turn conversations.
- **Routers:** always-strong, always-cheap, per-query, context-embedding and pattern-aware.
- **Metric:** quality at matched cost. The statistics and the pass rule are the same as for H1a.

## Change log

None yet.
