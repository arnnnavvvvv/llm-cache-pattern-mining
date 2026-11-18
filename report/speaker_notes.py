# slide-by-slide notes for the final review deck: what each slide shows, and what to say (also written into the deck)
NOTES = [
    {"title": "Title", "time": "20 s",
     "shows": "The project title, our guide, the SDP id and the four team members with registration numbers.",
     "say": "Good morning. We are presenting “Pattern-Mining-Driven Cache Admission and Routing for Multi-Provider LLM "
            "Gateways”, under the guidance of Dr. Sandipan Maiti. In one line: we built a cache for AI-model gateways that "
            "decides when a stored answer can be safely reused, by learning how real conversations behave."},
    {"title": "Presentation Outline", "time": "15 s",
     "shows": "The order of the talk: introduction, related work and our novelty, the proposed solution with standards, "
              "implementation and results, real-world applications and savings, and the summary.",
     "say": "We will cover the problem and our objectives, how existing systems fall short and what is new in our work, "
            "how the system is built, the results on real data, where it applies and what it saves, and a summary."},
    {"title": "Project Overview", "time": "60 s",
     "shows": "A one-paragraph description of the system on the left and four headline numbers on the right: 240× more "
              "requests served safely than a standard cache, 56.3% of near-duplicate requests answered wrongly by "
              "similarity caching, wrong reuse on corrections reduced from 66.7% to 0%, and 43 ms per decision.",
     "say": "Companies route AI requests through a gateway, and the gateway caches answers to save money and time. We built "
            "a behavior-aware admission engine for that cache. Instead of only checking how similar two requests look, it "
            "mines how conversations behave and uses that to decide whether reuse is safe. Four numbers summarise the "
            "project: a standard similarity cache gets 56.3% of near-identical requests wrong; our approach serves about "
            "240 times more requests at the same error level; mined patterns cut wrong reuse on corrections from 66.7% to "
            "zero; and each decision takes 43 milliseconds on a laptop."},
    {"title": "Problem Statement & Motivations", "time": "60 s",
     "shows": "Why the problem exists: model calls cost money and seconds; semantic caches reuse by similarity; but in real "
              "chats users iterate. The chart shows the dialogue role of all 30,015 turns: only 47.2% are fresh requests; "
              "follow-ups are 31.9%, new asks on the same material 9.0%, corrections 8.2%, continuations 3.8%.",
     "say": "Every call to a model like GPT or Claude is billed per token and takes seconds, so caching repeated requests is "
            "valuable. Today’s semantic caches reuse an answer when a new request is similar to an old one. The trouble is "
            "that conversations are not independent questions. When two different users type “make it shorter”, the text "
            "is identical but each refers to a different document. In our data, more than half of all turns — 52.8% — "
            "depend on the conversation. So the problem we solve is: for each request in a multi-turn stream, decide when a "
            "cached answer is genuinely safe to reuse."},
    {"title": "Objectives & Expected Impact", "time": "45 s",
     "shows": "Four objectives on the left (mine behavioral patterns; build the admission engine; evaluate rigorously on "
              "real traffic; deliver a deployable service and demo) and the expected impact on the right (lower cost and "
              "latency, fewer wrong answers, explainable decisions, a reusable evaluation method).",
     "say": "We set four objectives: mine behavioral patterns from gateway traffic, turn them into an admission engine, "
            "evaluate it rigorously on real data, and deliver it as a working service. The impact we aimed for is lower "
            "cost and latency, fewer wrong cached answers in chat products, decisions that can be explained, and a fair "
            "method for evaluating any cache. We will come back to each objective at the end with evidence."},
    {"title": "Related Work & Their Limitations", "time": "60 s",
     "shows": "Six existing systems — GPTCache, MeanCache, VectorQ, category-aware caching, ContextCache, and the routers "
              "FrugalGPT and RouteLLM — with their approach and limitation. The common gap: all of them decide from one "
              "request, at most with its own context.",
     "say": "GPTCache, the most widely used, applies one global similarity threshold. MeanCache learns the similarity per "
            "user, VectorQ adapts thresholds per region of the embedding space, and category-aware caching sets thresholds "
            "per topic. ContextCache, published in VLDB 2025, is the closest: it adds the current conversation’s history to "
            "the match. Routers like RouteLLM score one prompt at a time. The common gap is that none of them learns from "
            "the recurring behavior of the whole traffic stream — which is exactly what we do."},
    {"title": "Improvements over Existing Solutions", "time": "40 s",
     "shows": "A comparison grid: only our system uses context, mined behavior and the behavior of both sides of a reuse; "
              "and four improvements — mining across all traffic, conditioning on both the request and the cached entry, "
              "interpretable rules, and a fair evaluation at matched error rates.",
     "say": "The grid makes the difference concrete. ContextCache uses context, but only ours mines behavior across all "
            "sessions and users, and looks at the behavior of both the new request and the cached answer. That gives "
            "rules a person can read, and we evaluate every method at the same error rate on future data, which is the "
            "only fair comparison."},
    {"title": "Novel Contributions", "time": "60 s",
     "shows": "Four contributions: a new empirical finding on real traffic; behavioral states for caching; an "
              "association-rule reuse prior inside an expected-benefit rule; and a fair evaluation protocol. Bottom line: "
              "to our knowledge, the first semantic-cache admission conditioned on mined behavior of both sides of a reuse.",
     "say": "Our novelty has four parts. First, a finding: we measured on real traffic that reuse safety is governed by "
            "dialogue behavior — near-duplicates are wrong 56.3% of the time, 75.7% when the request depends on context "
            "versus 37.1% when it is self-contained. Second, we define behavioral states from mined act sequences for both "
            "the request and the cached entry. Third, association rules over those states give a reuse-safety prior "
            "inside an expected-benefit decision. Fourth, a rigorous replay-based evaluation protocol. To our knowledge, "
            "this is the first cache admission method built on mined behavior of both sides of a reuse."},
    {"title": "System Architecture", "time": "60 s",
     "shows": "The block diagram. Top: the online path for every request — client, embedder, candidate search, behavior "
              "features, admission decision, then serve from cache or call the model. Bottom: the offline loop — gateway "
              "log, act tagging, pattern mining, association rules, verifier training, with a reference judge providing labels.",
     "say": "The system has two halves. Online, every request is embedded, the three most similar cached requests are "
            "found, behavior features are computed, and the admission decision either serves the cached answer or calls "
            "the model. Offline, every day, the gateway log is tagged and mined using only past traffic; association rules "
            "and the verifier are learned from judged past reuses and pushed to the online path. Answers served from cache "
            "are never added back, so one wrong reuse cannot spread."},
    {"title": "Workflow", "time": "45 s",
     "shows": "The decision flow for one request, and the five steps: retrieve, describe, look up the rule prior, score "
              "with the verifier, decide by expected benefit.",
     "say": "For one request: we retrieve the top three earlier requests with similarity of at least 0.70; describe both "
            "turns by their dialogue act, intent and behavioral state; look up the mined rule for that pair; the LightGBM "
            "verifier turns all this into a probability that reuse is acceptable, discounted by the age of the entry; and "
            "we serve only if the expected benefit clears the threshold."},
    {"title": "Key Components / Modules", "time": "40 s",
     "shows": "Six modules: data ingest and replay, behavior tagger, pattern miner, rule learner, decision engine, and the "
              "service plus demo.",
     "say": "The implementation is six modules. Data ingest turns WildChat into gateway-style logs and the replay engine "
            "runs every policy with its own cache. The tagger labels five dialogue acts and twenty intents. The miner runs "
            "FP-Growth and PrefixSpan daily. The rule learner builds smoothed association rules. The decision engine "
            "combines them with a LightGBM verifier. And the FastAPI service and the five-page demo make it usable."},
    {"title": "Algorithms and Methods", "time": "60 s",
     "shows": "The methods and what each is used for, and the core formulas: the rule prior π(r), the validity q, the "
              "expected benefit B, the decision, and the HR@α score.",
     "say": "We use Sentence-BERT embeddings with FAISS search, k-means for intents, FP-Growth for frequent behavior sets and "
            "PrefixSpan for ordered sequences, class association rules for the safety prior, LightGBM as the verifier, and a "
            "session bootstrap with Holm correction for significance. The key formulas: the rule prior is the smoothed rate "
            "of acceptable reuse for a state pair; the expected benefit is U times q minus L times one minus q; we serve if "
            "it clears a threshold; and we score policies by HR at alpha — the most requests served while wrong answers "
            "stay under alpha."},
    {"title": "Technologies, Frameworks and Tools", "time": "25 s",
     "shows": "The tool stack grouped into data and ML, embeddings and search, pattern mining, labeling, service and demo, "
              "and quality and reporting.",
     "say": "The whole stack is open-source Python running on a CPU: pandas and scikit-learn, sentence-transformers and "
            "FAISS, mlxtend and prefixspan for mining, LightGBM, FastAPI for the service, Streamlit for the demo, and "
            "pytest with nineteen automated tests. Model APIs were used only to label data."},
    {"title": "Standards Followed", "time": "30 s",
     "shows": "Eight standards with where they apply — HTTP RFC 9110, JSON RFC 8259, OpenAPI 3.1, TLS 1.3, ISO 8601, "
              "Parquet, PEP 8, IEEE citations — and our engineering practices.",
     "say": "The service follows HTTP semantics and JSON, and publishes an OpenAPI 3.1 description. All model calls use TLS "
            "1.3. Timestamps are ISO 8601 in UTC, data is stored as Parquet, code follows PEP 8, and references follow IEEE "
            "style. On practice: everything is version-controlled with results tied to a release tag, tested "
            "automatically, and pre-registered; the data is public and anonymised, with toxic conversations excluded."},
    {"title": "Dataset / Input–Output", "time": "45 s",
     "shows": "The dataset per period — 30,015 turns, 6,828 sessions, 2,501 users, April 9–23 2023 — split by time into "
              "train, dev and a confirmation week; and the system’s inputs and outputs.",
     "say": "We used WildChat, a public dataset of real chatbot conversations that includes the answer each user actually "
            "received — exactly the shape of gateway logs. We kept English, multi-turn, non-toxic conversations: 30,015 "
            "turns. We split by time, 60/20/20, so the final test week is in the future relative to training, just like a "
            "real deployment. The system takes a session id, user id and request text, and returns whether to serve, the "
            "cached answer, the matched entry, the score, the dialogue act and the latency."},
    {"title": "Ground Truth Labels", "time": "45 s",
     "shows": "How correctness was labeled: candidates, the reference-based judge, the judge chosen from three models with "
              "85–88% agreement, 10,776 turns labeled with even coverage in every group (chart), and a human gold set.",
     "say": "To know whether a reuse was right, a judge model compares the cached answer with the answer the user actually "
            "got. We tested three judge models on the same 199 pairs; they agreed 85 to 88% of the time, and we chose the "
            "best balance of agreement and cost. We labeled 10,776 turns, about 89% of every group equally — the chart shows "
            "this — so the sample is representative. A two-rater human gold set is prepared to validate the judge."},
    {"title": "Parameters", "time": "20 s",
     "shows": "All key settings: similarity floor and candidates, intents, acts, mining supports, state length, rule "
              "smoothing, staleness half-life, costs, error levels, bootstrap and split — fixed before the final test.",
     "say": "These are the parameters. Important ones: similarity floor 0.70 with top-three candidates, minimum supports "
            "0.02 and 0.01 for mining, a 30-day staleness half-life, and evaluation at 5% and 10% wrong answers with 1,000 "
            "bootstraps. All were fixed in a configuration file before the final test."},
    {"title": "Outcome 1 — behavior decides safe reuse", "time": "70 s",
     "shows": "Wrong-reuse rate by similarity band and dialogue act. Below 0.97 similarity most reuse is wrong; among "
              "near-identical requests the act decides: fresh requests 37% wrong, follow-ups 74%, corrections 79%, "
              "continuations 88%. Stats: 56.3% overall, 75.7% vs 37.1%.",
     "say": "This is our central finding. Each group of bars is a similarity band; each colour is the type of turn. On the "
            "right, near-identical requests: if similarity were enough, these bars would all be low. Instead, fresh "
            "requests are wrong 37% of the time while follow-ups, corrections and continuations are wrong 74 to 88%. Over "
            "all 7,360 near-duplicates, a similarity cache is wrong 56.3% of the time. Similarity is necessary but not "
            "sufficient — conversational behavior decides."},
    {"title": "Outcome 2 — about 240× more requests served", "time": "70 s",
     "shows": "Share of requests served from cache at ≤10% wrong answers on the held-out week: similarity threshold 0.02%, "
              "per-intent thresholds 0.80%, context embedding 3.87%, our behavior-aware variants 4.62% and 4.49%. Gain "
              "+4.47 points, significant (p ≤ 0.002 after Holm), and robust to a stricter similarity floor.",
     "say": "Here is the main result on the held-out week. Each bar is the share of all requests a method answers from cache "
            "while keeping wrong answers at or under 10%. The GPTCache-style threshold manages 0.02% — to stay safe it has "
            "to be so strict it serves almost nothing. Our behavior-aware admission serves about 4.5% — roughly 240 times "
            "more — and more than the context-embedding approach at 3.87%. The gain over the standard cache is "
            "statistically significant at both error levels, and it holds when we tighten the similarity floor."},
    {"title": "Outcome 3 — ahead at every operating point", "time": "40 s",
     "shows": "Hit rate against wrong-reuse rate for every policy as its threshold is loosened; similarity baselines stay "
              "near zero, behavior-aware policies reach 4–5% at 10% and about 9% at 30%.",
     "say": "This chart shows the full trade-off: higher and further left is better. Whatever error level an operator "
            "chooses, the similarity baselines stay near zero, while the behavior-aware policies serve 4 to 5% at 10% "
            "error and about 9% at 30%. So the advantage is not a single lucky setting; it holds across the whole range."},
    {"title": "Outcome 4 — safer reuse", "time": "60 s",
     "shows": "Wrong reuse among served requests by dialogue act, with wrong/served counts on the bars: corrections 66.7% "
              "with the per-turn model vs 0% with mined patterns; follow-ups 15.4% → 13.3%; the context-embedding baseline "
              "is wrong on 30% of follow-ups.",
     "say": "Volume is one half; safety is the other. This chart looks only at requests each method chose to serve. On "
            "corrections, the per-turn model and the context baseline were wrong on two out of three; with mined patterns "
            "wrong reuse on corrections drops to zero. On follow-ups it falls from 15.4 to 13.3%, while the context-embedding "
            "approach was wrong on 30%. The patterns teach the system to refuse reuse in situations where it has failed "
            "before."},
    {"title": "Outcome 5 — interpretable rules", "time": "45 s",
     "shows": "The strongest and weakest mined rules with their acceptability and number of pairs; highlighted: reuse from "
              "a correction chain was acceptable 0% of the time (34 pairs), fresh-to-fresh 47% (2,643 pairs).",
     "say": "Every decision can be explained by a rule the system learned. For example, answering a fresh question with an "
            "answer that came out of a chain of corrections was never acceptable — zero out of 34. Fresh question to fresh "
            "question is the safest reuse, acceptable 47% of the time over 2,643 pairs. A similarity score cannot tell you "
            "any of this; our rules can, which matters for audits and debugging."},
    {"title": "Outcome 6 — validated results", "time": "50 s",
     "shows": "A positive control in which a planted behavioral effect is recovered (24.0% vs 5.7%), and the protocol: "
              "pre-registered, frozen single run, matched error rates, bootstrap with Holm, stable cross-validation, no leakage.",
     "say": "We took care that these results can be trusted. We wrote down the claims before testing, froze the code, and "
            "ran the final test once on a week the system had never seen. Every method is compared at the same error rate, "
            "with 1,000 bootstrap resamples and Holm correction. Cross-validation is stable at F1 0.63 to 0.64. And this "
            "chart is a positive control: when we plant a behavioral effect, our pipeline finds it — 24% versus 5.7% — "
            "showing the method detects such effects when they exist."},
    {"title": "Outcome 7 — deployable service", "time": "40 s",
     "shows": "Measured latency of the running service — 43 ms median and 79 ms at the 95th percentile in the engine, 54 / "
              "89 ms over HTTP, with 3,000 cached entries on a laptop CPU — and its OpenAPI documentation page.",
     "say": "This is not only an experiment; it runs as a service. A decision takes 43 milliseconds at the median on a "
            "laptop CPU with 3,000 cached entries, compared with the seconds a model call takes. On the right is the "
            "service’s automatically generated API documentation: a gateway calls /admit before forwarding a request and "
            "/record after the model answers."},
    {"title": "User Interface — replay and inspector", "time": "60 s",
     "shows": "Left: the replay of the held-out week with running hit rate and wrong-reuse counters, ending at exactly the "
              "reported numbers. Right: the decision inspector on an identical request whose cached answer belongs to "
              "another user’s follow-up chain — blocked by the mined rule.",
     "say": "Our demo replays the test week through the methods side by side; at the end the counters match the results "
            "we just showed. On the right is the inspector: here the new request and the cached one are word-for-word "
            "identical, similarity 1.0. But the cached answer was produced as a follow-up in someone else’s conversation, "
            "and the mined rule says that kind of reuse succeeded only 4% of the time. The judge confirms it would be wrong. "
            "A similarity cache would have served it; ours blocked it. (If time allows, show this live.)"},
    {"title": "User Interface — live admission and operating point", "time": "45 s",
     "shows": "Left: requests typed into the live service — repeated fresh questions are served, “make it shorter” is "
              "blocked as a follow-up. Right: choosing an error budget and reading every method’s hit rate off its real curve.",
     "say": "On the left, the live engine: a repeated fresh question like “Can you make some ASCII art?” is served from "
            "cache, while “make it shorter” is recognised as a follow-up and blocked, even though a similar text exists. "
            "On the right, an operator chooses how many wrong answers they can tolerate and sees how much each method would "
            "serve."},
    {"title": "Real-World Applications", "time": "45 s",
     "shows": "Six applications: enterprise LLM gateways, customer-support chatbots, coding and writing assistants, education "
              "bots, a guardrail for existing caches, and auditing AI caching; integration takes two HTTP calls.",
     "say": "Where does this apply? Any company running an LLM gateway can put our admission layer in front of provider "
            "calls. Customer-support and tutoring bots get many repeated fresh questions that can be served instantly. "
            "Coding and writing assistants are full of refinement loops where similarity caching fails, and our system "
            "protects them. Even teams that keep their existing cache can adopt our rule: never reuse for follow-ups, "
            "corrections or continuations. And the mined rules plus our replay protocol let teams audit caching decisions. "
            "Integration is just two HTTP calls."},
    {"title": "Projected Savings", "time": "60 s",
     "shows": "Savings over an industry-standard similarity cache at the same ≤10% error: extra calls avoided and rupee "
              "savings per month and year for 1M, 10M and 100M requests a month, on a premium and a budget model; ₹1.95 "
              "crore a year at 100M requests; 44,712 vs 187 calls avoided per million; the formula and assumptions.",
     "say": "What is it worth? Per million requests, our method avoids 44,712 model calls against 187 for a standard cache "
            "at the same error rate. Multiplying by the real price we paid per call — about 36 paise on a premium model — "
            "a startup with a million requests a month saves about ₹1.95 lakh a year, a mid-size company about ₹19.5 lakh, "
            "and an enterprise at 100 million requests about ₹1.95 crore a year. These are conservative: real calls also "
            "send the conversation history, which makes every avoided call more expensive."},
    {"title": "Objectives Met", "time": "40 s",
     "shows": "Each objective with its status and evidence: patterns mined (82 rules), admission engine (~240×), safer reuse "
              "(66.7% → 0%), rigorous evaluation (30,015 turns, single frozen test), service and demo (43 ms), real-world value "
              "(₹1.95 crore a year at enterprise scale).",
     "say": "Coming back to our objectives: we mined behavioral patterns and learned 82 rules; built the admission engine "
            "that serves about 240 times more than a standard cache; made reuse safer on corrections; evaluated it "
            "rigorously on 30,015 real turns with a frozen, single test; delivered a 43-millisecond service with a demo; "
            "and showed its value in rupees. Every objective is achieved, with evidence."},
    {"title": "Summary", "time": "45 s",
     "shows": "Key findings, limitations (one dataset over two weeks; LLM-judge labels with human rating in progress; the "
              "live tagger can improve) and future directions (routing and conversation-level fast-tracking, larger workloads, "
              "live deployment).",
     "say": "To summarise: behavior, not similarity, decides whether a cached answer is safe; behavior-aware admission "
            "serves about 240 times more requests at the same error; mined patterns make reuse safer and explainable; and "
            "it runs in 43 milliseconds. Our limitations are one public dataset over two weeks, labels from an AI judge "
            "whose human validation is in progress, and a live tagger that can be improved. Next, we will extend the same "
            "behavioral signals to model routing and conversation-level caching — which we have already begun exploring — "
            "test on larger workloads, and deploy inside a live gateway."},
    {"title": "Bibliography", "time": "10 s",
     "shows": "The fourteen key references: the caching systems we compare with, the routing work, the WildChat dataset, "
              "LLM-as-a-judge, and the algorithms we use.",
     "say": "These are our main references; the full list of twenty-two is in the report."},
    {"title": "Thank you", "time": "—",
     "shows": "Closing slide.",
     "say": "Thank you. We are happy to take questions, and we can show the demo live."},
]

# answers to the questions examiners are most likely to ask, for the presenters
QA = [
    ("Does mining beat dialogue acts alone?", "Acts carry most of the volume gain — both our variants serve about 4.5% — "
     "and the mined patterns add safety (corrections 66.7% → 0%) and explainable rules. Both are part of our behavior-aware approach."),
    ("How do you know a reuse was wrong?", "A judge model compares the cached answer with the answer the user really got; "
     "three different judges agree 85–88%; a two-rater human gold set is prepared."),
    ("Why is the fixed threshold so low?", "Even near-identical requests are wrong 56% of the time, so a threshold strict "
     "enough to keep errors at 10% serves almost nothing."),
    ("How is ContextCache different?", "It matches the current conversation’s text; we mine behavior across all sessions and "
     "users and look at both sides of a reuse. Our context-embedding baseline was wrong on 30% of follow-ups."),
    ("Are the savings real?", "The calls avoided are measured on held-out data; the rupee figure multiplies them by the price "
     "we actually paid, and excludes conversation history, so it is conservative."),
    ("Could the results be overfitted?", "The final test ran once, on frozen code, on a later week never used in design; "
     "patterns use only past traffic; 19 tests check for leakage."),
]
