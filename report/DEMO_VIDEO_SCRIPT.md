# Demo video script (about 7 minutes)

Recording setup: start the demo with `streamlit run demo/app.py` and open http://localhost:8501 in a browser at
1500×950 or larger. Open the Live admission page once before recording so the model and the 3,000 cached entries are
already loaded (about a minute). Record the screen with the Windows Game Bar (Win + Alt + R) or OBS. Every number
spoken below is on screen at that moment.

## 1. Opening, 0:00–0:40 (slide 1, then slide 2 of the deck)

Show: title slide, then the "Semantic caches reuse answers by similarity alone" slide.

Say: "LLM gateways save money and time by answering repeated requests from a cache. Today's semantic caches reuse an
answer whenever a new request looks similar to an old one. But more than half of the 30,015 real chat turns we
replayed are follow-ups, corrections or continuations that only make sense inside their own conversation. Our
question: can patterns mined from the traffic itself tell safe reuse from unsafe reuse?"

## 2. The finding, 0:40–1:30 (demo, Findings page)

Show: Findings page, the three numbers at the top, then the bar chart.

Say: "Among 7,360 near-duplicate requests, a similarity cache serves an unacceptable answer 56.3% of the time. The
dialogue act decides how often: 75.7% wrong when the request depends on context, 37.1% when it is self-contained.
Similarity alone cannot see this."

## 3. Replay, 1:30–3:00 (demo, Replay page)

Show: Replay page. Drag the slider to about 450, point at rows where P3 is "served, WRONG" and P4 is "call LLM". Turn
on Play for a few seconds, then drag to the end (2,424).

Say: "This replays the held-out confirmation period, which we evaluated only once, on frozen code. Each column is a
policy: P1 is a fixed similarity threshold like GPTCache, P3 is a learned verifier that knows each turn's dialogue act,
and P4 adds our mined patterns and association rules. Each one keeps its own cache. At the end of the period the
counters equal the confirmation table: P1 serves 0.02% of requests, P3 4.62% and P4 4.49%, all with wrong reuse
under 10%. That is about 240 times the fixed threshold. P3 and P4 tie on volume, which is why our strict
pre-registered criterion was not met."

## 4. Why a decision was made, 3:00–4:30 (demo, Inspect a decision)

Show: "P3 served a wrong answer, P4 refused", first request. Point at the identical texts, the two states, the 4%
rule, the judge verdict and the decision table.

Say: "Here the new request is word for word identical to a cached one, so similarity is 1.0. But the cached answer
was produced as a follow-up inside another user's refinement loop. Our miner places it in the state 'follow-up after
follow-up', and the learned rule says reuse from that state was acceptable only 4% of the time in the past. The
judge agrees it is not acceptable. P3 served it; P4 refused it. Across the period, the per-turn and context policies
served three corrections and got two wrong; the pattern policies served one and got it right."

Then switch the filter to "P4 served a correct answer" and show one served reuse.

## 5. Operating point, 4:30–5:15 (demo, Operating point)

Show: drag the slider from 5% to 10% to 20%.

Say: "A gateway operator chooses how many wrong answers they can tolerate. At every budget, the learned policies serve
far more than the threshold policies, which stay near zero until wrong reuse is very high."

## 6. Live service, 5:15–6:15 (demo, Live admission)

Show: type "Can you make some ASCII-art please?", Send; then "make it shorter", Send; then
"Where can I use chatgpt 4 for free", Send.

Say: "This is the running admission service with 3,000 real cached entries. A repeated fresh question is served from
cache. 'Make it shorter' is tagged as a follow-up, its score falls below P4's threshold, and it is blocked even though
a similar request exists in the cache. Each decision takes well under a second here; the benchmarked engine takes 43
milliseconds at the median on this laptop CPU."

## 7. Honest results and close, 6:15–7:00 (deck slides 12 and 17)

Show: "What did not work" slide, then Conclusion.

Say: "Two parts did not work at this scale: pattern-aware routing was no better than random, and fast-tracking whole
conversations would have satisfied only 4.8% of users. We report both. The main takeaway: whether a cached answer can
be reused is a behavioral question, and mining that behavior gives a cache that knows when similarity is misleading.
Thank you."
