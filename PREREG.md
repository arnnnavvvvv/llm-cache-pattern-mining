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

- **2026-11-16, judge model.** The primary judge moves from `openai/gpt-oss-120b` (Groq) to `claude-sonnet-5.5` (Anthropic models through an Anthropic-compatible gateway).
  - **Reason:** the Groq free tier caps each model at about 200K tokens a day, enough for only a few hundred turns.
  - **How it was chosen:** on 100 training-period turns (199 pairs), Haiku 5.5, Sonnet 5.5 and Opus 5.5 agreed with each other on 85-88% of pairs. Sonnet was picked on cost and quality.
  - **Timing:** this was decided before any confirmation-period label existed.
  - **Gold set:** those 199 pairs, labeled by all three models, become the human gold set, so each judge is validated against the raters.
- **2026-11-16, dialogue acts.** The fast act tagger reached only 0.47 macro-F1 against 1,000 LLM seed labels, below the 0.70 gate.
  - **Change:** every turn is now tagged directly by `claude-haiku-5.5`.
  - **Service:** the fast classifier is retrained on those tags, for the live service only.
  - **Timing:** this was decided before any pattern feature was computed.
- **2026-11-16, label coverage.** Labeling stopped at 10,776 of 12,124 queued turns (88.9%) when the labeling budget ran out.
  - **Why this is still a valid sample:** the queue is randomly interleaved within each period × similarity stratum, so the labeled turns are a stratified random sample. Coverage is 88.5-89.3% in every stratum, and all metrics are reweighted to the stratum populations.
  - **Timing:** this was decided before any confirmation-period result was computed.
- **2026-11-16, curve resolution.** The hit-rate/wrong-reuse curve was read at 80 evenly spaced quantile thresholds. On the dev period that left no threshold between "serve one turn" and about 0.5% hit rate, which zeroed out the strict-level readout for policies with continuous scores.
  - **Change:** the grid now has 300 thresholds over the top 30% of best scores plus 60 below. The replay is unchanged except that it skips turns that cannot be served at a given threshold.
  - **Scope:** the change applies identically to every policy.
  - **Timing:** this was decided on dev results and logged before the confirmation run.
- **2026-11-16, behavioral states and association-rule prior.** Two additions to the pattern feature set (P4, P4+), designed from the hypothesis and tested once on dev.
  - **Behavioral state:** each request and each cache entry gets the longest frequent act-sequence suffix it sits in, from the daily-mined patterns. Two features come from it: whether the two states match, and the mined confidence of the entry's own act.
  - **Rule prior:** a smoothed class-association-rule estimate of reuse acceptability per (request state, request act, entry state, entry act), mined from training-period labels only, out-of-fold for training rows.
  - **Dev result:** P4's hit rate at ≤10% wrong-reuse went from 1.81% to 1.93%. No further changes after this entry. Confirmation follows under the freeze tag.
