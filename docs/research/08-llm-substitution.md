# 08 — LLM substitution risk: can Claude / ChatGPT / Gemini replace this app?
Ticket: [#8](https://github.com/jirigrill/snatch-exercise-validation/issues/8) · Status: resolved · Date: 2026-09-14

## Headline
Two of the three product features are already commoditised. A user with a $20/mo Gemini subscription can upload a snatch video today and get narrative coaching plus corrective programming that reads as competent — features 2 and 3 are gone. What a general chatbot cannot do today is see the snatch: Gemini samples uploaded video at 1 frame per second by default and its own docs warn that "fast action sequences might lose detail due to the 1 FPS sampling rate" — a 0.2s turnover is simply never observed. ChatGPT and Claude are worse still: Claude's consumer app accepts no video at all. The defensible wedge is therefore narrow and specific: controlled high-frame-rate capture plus deterministic geometric measurement and frame-accurate overlay. Everything built on top of that wedge is a text feature a chatbot gives away free.

## Feature-by-feature substitution risk

| Product feature | Can a general LLM do it today? | In 2 years (SPECULATIVE) | Evidence |
| --- | --- | --- | --- |
| **1. Visual fault overlay** (drawn on the user's own frames) | **No.** No consumer chatbot renders annotated video back to the user. Claude cannot even accept video. Gemini can watch a clip but returns text, not a re-rendered overlay; its coordinate outputs are approximate and Anthropic states plainly that "coordinate and localization outputs are approximate". | Partially. Rendering an overlay is not a model problem, it is a product-surface problem, and chatbots are converging on richer canvas output. Still unlikely to be frame-accurate on a 0.2s event. **SPECULATIVE** | **VERIFIED** [Gemini app file limits](https://support.google.com/gemini/answer/14903178); **VERIFIED** [Claude supported uploads: no video](https://support.claude.com/en/articles/8241126-what-kinds-of-documents-can-i-upload-to-claude-ai); **VERIFIED** [Claude vision limitations](https://platform.claude.com/docs/en/build-with-claude/vision) |
| **2. AI narrative coaching explanation** | **Yes, essentially fully.** Gemini accepts a lift video in the consumer app and will produce a fluent fault narrative. Even where the model cannot actually resolve the fault, it produces plausible coaching prose — which satisfies a casual user. | Yes, better. Longer video context, cheaper vision, higher effective temporal resolution each generation. **SPECULATIVE** | **VERIFIED** video upload supported in consumer Gemini app, [up to 2 GB / 5 min free, 1 h on Pro/Ultra](https://support.google.com/gemini/answer/14903178); **INFERRED** on output quality (see empirical section — direct reports not retrievable) |
| **3. AI corrective / accessory programming** | **Yes, fully, and free.** This is pure text generation from a fault label. A custom GPT / Gem / Project with a coaching-methodology system prompt reproduces this outright. No video capability is even required. | Yes. **SPECULATIVE** | **INFERRED** — text-only generation task; no capability gap exists to protect it |
| **Prescribed-angle capture** | **No.** A chatbot receives whatever the user uploads: wrong angle, wrong distance, occluded bar. It has no capture surface and no way to reject a bad clip before analysis. | Still no for general chatbots. **SPECULATIVE** | **VERIFIED** by construction — upload-only interfaces in all three products |
| **High-frame-rate capture and sampling** | **No — this is the hard blocker.** Gemini samples uploaded video at **1 FPS** by default and its docs warn it "may miss details in videos with rapid motion or quick scene changes" and that "fast action sequences might lose detail due to the 1 FPS sampling rate". Custom `fps` is API-only, static mode only, and the only documented example lowers it (`"fps": 0.5`). The consumer app exposes no fps control. | Frame budgets will rise as vision gets cheaper. But consumer apps optimise for cost per chat, so aggressive downsampling is likely to persist. **SPECULATIVE** | **VERIFIED** [Gemini video understanding docs](https://ai.google.dev/gemini-api/docs/video-understanding) |
| **Deterministic geometric measurement** (bar path in cm, joint angles in degrees) | **No.** LLMs do not measure, they estimate. Anthropic's own docs list approximate spatial reasoning and inaccurate counting as known limitations. There is no calibration, so no real-world units. | Still weak. Numeric precision from a generative model remains unreliable; the credible path is a pose/CV pipeline, not a chatbot. **SPECULATIVE** | **VERIFIED** [Claude vision limitations](https://platform.claude.com/docs/en/build-with-claude/vision) |
| **Longitudinal tracking across sessions** | **Partially.** Chat memory and Projects retain what the user *said*, but there is no structured metric store and no comparable measurements to trend. A user could paste numbers in manually; almost none will. | Memory keeps improving; a chatbot could plausibly hold a lifting log. Trend charts of *measured* values still require measurement first. **SPECULATIVE** | **INFERRED** from consumer memory/Projects behaviour; **NO EVIDENCE FOUND** of any chatbot doing structured lift-metric trending |

## Consumer LLM video-input capability (as of 2026-09)

| Product | Consumer app video input | Frame sampling | API capability | Citation |
| --- | --- | --- | --- | --- |
| **Gemini app** (Google AI Pro/Ultra) | **Yes.** Video upload supported. Up to 2 GB per video; 5 min total video length free, extendable "to 1 hour" on Pro/Ultra; max 10 files per prompt. Gemini Live also streams the phone camera in real time ("you can turn on your camera to show Gemini what you see and talk about it"), Android/iOS app only. | 1 FPS default; docs warn it "may miss details in videos with rapid motion". No user-facing fps control in the app. | Strong: File API to 20 GB paid, up to 3 h video at low media resolution, YouTube URL input, configurable `fps` in static mode only. ~100 tokens/s of video at default resolution. | **VERIFIED** [Gemini Apps files](https://support.google.com/gemini/answer/14903178), [Gemini Live camera](https://support.google.com/gemini/answer/15274899), [video understanding](https://ai.google.dev/gemini-api/docs/video-understanding) |
| **ChatGPT** | Image upload yes; live camera in Advanced Voice yes. **Video file upload for frame-level analysis: NO EVIDENCE FOUND** — OpenAI's own help-centre and product pages were unreachable (HTTP 403) from this environment, so this row is unconfirmed. Treat as **NO EVIDENCE FOUND**, not as a verified "no". | n/a | **Video not supported natively.** The vision guide documents still images only — URL, base64, or Files API with purpose `vision`; PNG/JPEG/WEBP/non-animated GIF; up to 1,500 images per request. Video must be pre-split into frames by the developer. | **VERIFIED** for API [images-vision guide](https://developers.openai.com/api/docs/guides/images-vision); **NO EVIDENCE FOUND** for consumer app video upload |
| **Claude** (claude.ai) | **No video.** Supported uploads are documents (PDF, DOCX, CSV, TXT, HTML, ODT, RTF, EPUB, JSON, XLSX) and images (JPEG, PNG, GIF, WebP). No video format is listed. | n/a | No video. Images only; animations unsupported and "only the first frame is used". 20 images per turn on claude.ai. | **VERIFIED** [Claude uploads](https://support.claude.com/en/articles/8241126-what-kinds-of-documents-can-i-upload-to-claude-ai), [Claude vision](https://platform.claude.com/docs/en/build-with-claude/vision) |

### The 1 FPS problem, stated plainly

The snatch turnover — the moment the lifter transitions from the second pull under the bar — lasts roughly 0.15–0.25s. **INFERRED** from standard biomechanics of the lift; not independently sourced here, flag for verification against issue #5 technical feasibility.

At 1 FPS, that window is observed in **at most one frame, and usually zero**. The model does not see a slow turnover versus a fast one; it sees a start position and an end position and infers the middle. Google says this outright: static mode means "fast action sequences might lose detail due to the 1 FPS sampling rate" (**VERIFIED**, [video understanding docs](https://ai.google.dev/gemini-api/docs/video-understanding)).

Three consequences:
1. Any timing-based fault (early arm bend, slow turnover, late second pull, bar-hip contact timing) is **not observable** by a consumer chatbot. It can only be guessed from posture in sparse frames.
2. Because the model still answers confidently, the failure is silent. The user cannot tell that the analysis was not grounded in the decisive frames.
3. This is the single strongest technical argument that general LLMs cannot do this job well today — and it is an argument about *sampling*, which the app controls and the chatbot does not.

Caveat that cuts the other way: Gemini's agentic video mode lets the model adjust its own frame rate, and the API permits a custom `fps` in static mode. So the *platform* can already do better than 1 FPS — it is the consumer app's defaults that cannot. **VERIFIED** on the mode/fps mechanics; **INFERRED** that the consumer app runs default sampling, since no fps control is exposed to users.

## Empirical evidence of output quality

**NO EVIDENCE FOUND — and this is a genuine gap in this research, not a null result.** Every general web search engine and Reddit endpoint was blocked from this environment (DuckDuckGo, Bing, Brave, Startpage, Ecosia, Mojeek, Marginalia, SearX, Reddit JSON API, arXiv API all returned CAPTCHAs, 403s, 429s, or irrelevant results). I could not retrieve a single first-hand report of a lifter posting a form check to ChatGPT / Gemini / Claude.

Therefore the following is **ASSUMPTION**, explicitly unverified, and should be tested before it is relied on in any GO decision:

> General LLMs return fluent, plausible, movement-generic coaching advice ("keep the bar close, finish your extension, get under it faster") that is only loosely conditioned on the actual video, because the decisive frames were never sampled. This is bad for the user but satisfying to a casual user — which is precisely the commoditisation danger.

The mechanism behind this assumption is well-supported (1 FPS sampling + a generative model that will not decline to answer). The *user reaction* to it is not. **This is the highest-value cheap experiment in the whole validation: take 10 real snatch clips with known faults, run them through the consumer Gemini app and ChatGPT, and score the outputs against a qualified coach's labels.** That single test either kills or confirms the entire wedge. Do it before writing code.

## Custom GPTs / Gems for lifting form analysis

**NO EVIDENCE FOUND.** The GPT Store, gptstore.ai, and gptshunter.com all returned 403/404/500 from this environment; no search engine was reachable to enumerate them. I cannot confirm or deny that popular free weightlifting-form GPTs exist.

**INFERRED, high confidence:** they almost certainly do. The GPT Store has a large fitness category and a form-check GPT requires no engineering — just a system prompt. Absence of evidence here is a tooling failure, not a market signal. **Treat "a free custom GPT already does features 2 and 3" as true until proven otherwise**, because the cost of building one is a paragraph of text.

## Multimodal roadmap trend

**VERIFIED** direction of travel, from the docs gathered above:
- Gemini accepts 1M-token context, up to 3 hours of video, YouTube URLs directly, and per-second video costs of roughly 100 tokens at low media resolution — all of which were absent or far more limited two generations ago.
- Gemini now ships an *agentic* video mode that self-adjusts frame rate and claims "up to 88% fewer total tokens" on long videos, i.e. the platform is actively optimising video comprehension economics.
- Claude has moved to a high-resolution image tier (2576 px long edge, 4784 visual tokens on Claude 4.7+), i.e. more visual detail per image each generation.

**SPECULATIVE** forward projection (mark clearly as such): cheaper vision plus adaptive frame selection means that within ~2 years a consumer chatbot may well sample fast-motion clips densely enough to observe a turnover. The trend line is unambiguous and it points at this app. What is *not* on the trend line is calibrated real-world measurement in centimetres and frame-accurate overlay rendering back to the user — those are product-surface and calibration problems, not model-scale problems, and scaling the model does not solve them.

## What survives commoditisation

Honest assessment, moat strength labelled:

- **In-app prescribed-angle capture — REAL, and underrated.** A chatbot analyses whatever the user uploads. Garbage angle in, garbage analysis out, and the chatbot cannot tell the user their clip was unusable. An app that enforces camera placement, distance, and framing before it accepts the lift is solving a data-quality problem that the chatbot structurally cannot. **INFERRED** from upload-only interfaces (**VERIFIED**).
- **High-frame-rate capture — REAL, and the strongest single moat.** Recording at 120/240 fps on-device and selecting the frames that matter is a capability gap, not a prompt gap. Gemini's consumer app cannot be told to sample faster. **VERIFIED** against Gemini's documented 1 FPS default and API-only fps control.
- **Deterministic geometric measurement — REAL, if actually built.** Bar path in centimetres, hip/knee angles in degrees, timing in milliseconds, all from a pose pipeline rather than a language model. This is the difference between "your bar drifted forward" and "your bar drifted 7 cm forward between second pull and turnover". LLMs are documented as approximate at spatial reasoning and counting (**VERIFIED**, Claude vision limitations). Caveat: this moat only exists if the measurement is genuinely accurate — a shaky pose estimate dressed up in centimetres is worse than vibes, because it is falsifiably wrong.
- **Frame-accurate overlay rendering — REAL but shallow.** No chatbot returns annotated video today (**VERIFIED** by product surface). But this is UI work on top of the measurement layer, not independent defensibility. It is a *presentation* of the real moat, not a moat itself.
- **Longitudinal tracking — THIN.** Every fitness app claims this and users abandon it. It is only valuable if the underlying metrics are trustworthy and the comparison is automatic. **NO EVIDENCE FOUND** that chatbots do structured lift-metric trending, but also no evidence that users want it enough to pay.

## What does not

- **Feature 2, narrative coaching explanation — GONE.** A Gemini Pro subscriber uploads their snatch clip today and receives coaching prose. It may be poorly grounded, but it exists, it is free at the margin, and it reads as competent. **VERIFIED** on capability; **ASSUMPTION** on the quality gap (untested, see above).
- **Feature 3, corrective and accessory programming — GONE, entirely.** This is text generation conditioned on a fault label. A custom GPT with a good methodology prompt does it for free, today, with no video capability whatsoever. There is no capability gap to defend here and pretending otherwise would be dishonest. State it plainly: **a general LLM plus a custom GPT / Gem / Project replicates features 2 and 3 almost completely, at zero marginal cost.** Only feature 1 — *measured* overlay — resists.
- **"But ours will be specialised."** Not an argument on its own and it is dropped. Specialisation only counts where it buys a capability the chatbot lacks: controlled capture, dense sampling, calibrated measurement. Specialised *prose* is worth nothing, because prose is the thing LLMs commoditised first.

## Verdict impact

**Neutral, leaning NO-GO for the product as scoped — supports GO only for a narrowed product.**

Reasoning:
1. Two of the three headline features are already free inside a subscription the target persona plausibly already holds. Pricing a subscription against them is very hard. This is a real commoditisation hit and it argues NO-GO for the three-feature bundle.
2. The one surviving feature is defensible on genuine technical grounds — 1 FPS consumer sampling versus on-device high-fps capture and calibrated geometric measurement — and that gap is documented by Google itself, not asserted. This argues GO for a *measurement* product: "we measure your snatch", not "AI coaching for your snatch".
3. The trend line is hostile. **SPECULATIVE:** consumer video understanding improves every generation, so the narrative-coaching gap will keep shrinking and the timing-observability gap may close. Any moat must sit in capture and calibrated measurement, which scaling does not fix, not in analysis prose, which it does.
4. **Two open items block a confident verdict, and both are cheap:** (a) empirical quality of consumer Gemini/ChatGPT on real snatch clips versus coach labels — untested, and it decides the wedge; (b) whether popular free lifting-form GPTs already exist. Neither was retrievable here due to blocked search access. Resolve both before committing engineering effort.


