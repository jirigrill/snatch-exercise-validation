# 06 — Unit economics: per-analysis cost and the subscriber count for $1–3k/month net
Ticket: [#6](https://github.com/jirigrill/snatch-exercise-validation/issues/6) · Status: resolved · Date: 2026-09-14

All prices retrieved **2026-09-14** from official pricing pages. Every line is either **VERIFIED** (a cited published price) or **INFERRED**/**ASSUMPTION** (a usage assumption, challengeable independently).

---

## Headline

Raw per-analysis cost is trivial — **$0.006–$0.012** for a 10-second snatch under any sane architecture. Cost is **not** the binding constraint; the binding constraints are (a) the free tier, which at a 2.9% conversion rate loads **33.5 non-paying users onto every payer** and can quietly consume 20–75% of net revenue, and (b) demand. At $9.99/mo with on-device pose extraction you need **~167 paying subscribers for $1k net** and **~488 for $3k net**; at $4.99 you need **474 / 1,379**, which is a materially harder marketing problem for the same money. If you instead pick the naive architecture (full-frame cloud video LLM at high fidelity on Gemini Pro) plus a generous free tier at 1% conversion, **net per subscriber is negative $44** — the product loses money on every sale. Architecture choice, not pricing, decides whether this business exists.

---

## 1. VERIFIED prices (retrieved 2026-09-14)

### 1.1 Object storage

| Provider | Storage $/GB-month | Egress $/GB | Notes | Source |
|---|---|---|---|---|
| **Cloudflare R2 Standard** | **$0.015** | **$0.00 (zero egress)** | Class A $4.50/M, Class B $0.36/M; free tier 10 GB-mo | [R2 pricing](https://developers.cloudflare.com/r2/pricing/) |
| Cloudflare R2 Infrequent Access | $0.010 | $0.01/GB retrieval | Class A $9.00/M, Class B $0.90/M | same |
| **AWS S3 Standard** (us-east-1) | **$0.023** (first 50 TB) | **$0.09/GB** (Ireland example rate; first 100 GB/mo free across AWS) | $0.022 next 450 TB, $0.021 >500 TB; GET $0.0004/1k | [S3 pricing](https://aws.amazon.com/s3/pricing/) · rates confirmed via [AWS Price List API](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonS3/current/index.json) |
| **Backblaze B2** | **$0.00695** ($6.95/TB/mo) | **$0.00 up to 3× stored bytes**, then $0.01/GB | Class A/B/C API calls free; free egress to Cloudflare/bunny.net | [B2 pricing](https://www.backblaze.com/cloud-storage/pricing) |
| **Bunny Storage** Standard (HDD) | **$0.01** per region (≤2 regions) | Free to Bunny CDN; CDN billed separately | $0.005/GB per extra region; $1/mo minimum | [Bunny Storage pricing](https://bunny.net/pricing/storage/) |
| Bunny Storage Edge (SSD) | $0.02 per region | same | up to 15 regions | same |
| Bunny CDN bandwidth | — | **$0.01/GB** EU+NA standard; **$0.005/GB** volume network | $0.03 APAC, $0.045 LATAM, $0.06 MEA | [Bunny pricing](https://bunny.net/pricing/) |
| Hetzner Storage Box BX11 | 1 TB, unlimited free traffic | **$0.00 (traffic free)** | **PRICE NOT VERIFIED** — Hetzner renders monthly prices client-side; the figure did not load on the [Storage Box page](https://www.hetzner.com/storage/storage-box/) or [docs](https://docs.hetzner.com/storage/storage-box/general/). Excluded from all arithmetic rather than guessed. | [Storage Box](https://www.hetzner.com/storage/storage-box/) |

**Conclusion: R2 wins for this product** despite not being the cheapest per GB, because a form-analysis app re-serves the same clip on every review and R2's zero egress removes the variable that kills S3. At $0.09/GB S3 egress, a single replay of a 20 MB clip costs **$0.00176** — more than a month of storing it in R2 ($0.000293). **VERIFIED** arithmetic from the rates above.

### 1.2 Video processing / delivery platforms

| Provider | Storage | Delivery | Encoding | Source |
|---|---|---|---|---|
| **Cloudflare Stream** | **$5 / 1,000 min/mo** ($0.005/min-mo) | **$1 / 1,000 min** ($0.001/min) | Free | [Stream pricing](https://developers.cloudflare.com/stream/pricing/) |
| **Mux Video** (720p basic) | **$0.0024/min-mo**; 1080p $0.003, 2K $0.0048, 4K $0.0096 | **$0.0008/min** 720p; $0.001 1080p; 100k free min/mo | Free at basic; Plus $0.025/min 720p | [Mux video pricing](https://www.mux.com/pricing/video) |
| **Bunny Stream** | **from $0.01/GB** | **from $0.005/GB** | **Free**, no transcoding fees | [Bunny Stream pricing](https://bunny.net/pricing/stream/) |
| **api.video** | **$0.00285/min-mo** | **$0.0017/min** | Free, unlimited minutes | [api.video pricing](https://api.video/pricing/) |

**All four are irrelevant to this product.** They price per *minute* on the assumption of long-form playback. A 10-second clip is 0.167 min; Cloudflare Stream storage is $0.000833/mo and three deliveries cost $0.0005 — cheap in absolute terms but ~3× R2 for storage, and you are paying for an HLS/DASH ladder you do not need. A snatch clip is replayed frame-by-frame with an overlay drawn locally; it should be a single MP4 in R2, not an adaptive-bitrate stream. **INFERRED** from the delivery model.

### 1.3 Multimodal / video LLM inference

**The single most important VERIFIED fact in this document:** Gemini samples video at **1 frame per second by default**, and each frame costs **66 tokens at low `media_resolution`** or **258 tokens otherwise**. Audio is **32 tokens/second**. Source: [Gemini video understanding docs](https://ai.google.dev/gemini-api/docs/video-understanding). This is the cost lever — a 10× change in `fps` is a 10× change in inference cost, and the default (1 fps) is **useless for a snatch**, where the entire second pull → turnover → catch sequence happens in roughly 1.2–1.8 seconds.

| Model | Input $/1M | Output $/1M | Source |
|---|---|---|---|
| Gemini 3 Flash Preview | **$0.50** (text/image/video), $1.00 audio | **$3.00** | [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing) |
| Gemini 3.1 Pro Preview | **$2.00** (≤200k ctx) | **$12.00** | same |
| Gemini 2.5 Flash | $0.30 text/image/video, $1.00 audio | $2.50 | same |
| Gemini 2.5 Flash-Lite | **$0.10** text/image/video | **$0.40** | same |
| Gemini 3.5 Flash-Lite | $0.30 | $2.50 | same |
| OpenAI gpt-5 | **$1.25** ($0.125 cached) | **$10.00** | [OpenAI API pricing](https://developers.openai.com/api/docs/pricing) |
| OpenAI gpt-5-mini | **$0.25** | **$2.00** | same |
| OpenAI gpt-5-nano | $0.05 | $0.40 | same |
| OpenAI gpt-5.6-luna | $0.20 short-ctx | $1.20 | same |
| Anthropic Haiku 4.5 | **$1.00** | **$5.00** | [Claude pricing](https://claude.com/pricing) |
| Anthropic Sonnet 5 | $2.00 | $10.00 | same |
| Anthropic Opus 5 | $5.00 | $25.00 | same |

**Caveat on OpenAI (VERIFIED absence):** OpenAI's pricing page publishes **no flat per-image token rate** — it directs you to an image input cost calculator. So any OpenAI vision figure below rests on an **ASSUMPTION** of tokens-per-image and is flagged as such. Anthropic and Google are used for the load-bearing numbers because their per-frame token accounting is published.

### 1.4 Distribution and payment costs

| Line | Rate | Source |
|---|---|---|
| **Apple App Store standard commission** | 30% | [Small Business Program](https://developer.apple.com/app-store/small-business-program/) |
| **Apple Small Business Program** | **15%**, eligibility **≤ $1M USD proceeds** in prior fiscal year AND current year; developers new to the App Store also qualify | same |
| Apple SBP + EU alternative terms | 10% on subscriptions after year one | same |
| Apple bonus (relevant!) | SBP members with **<2M first-time downloads** may use **Apple Foundation Models on Private Cloud Compute at no cloud API cost** (requires PCC entitlement) | same |
| **Google Play auto-renewing subs** | **15%** outside EEA/UK/US for first $1M/yr; **10% + 5% billing fee** in EEA/UK/US from 2026-06-30 | [Play service fees](https://support.google.com/googleplay/android-developer/answer/112622) |
| **Stripe** (AT/EEA published rates) | **1.5% + €0.25** EEA standard cards; 2.8% + €0.25 EEA premium; 3.15% + €0.25 other international; +2% currency conversion; €20 per dispute | [Stripe pricing](https://stripe.com/pricing) |
| Stripe Tax Basic | 0.5% per transaction (no-code) or €0.45/transaction (API) | same |
| **Paddle** | **5% + $0.50** per checkout transaction, tax compliance included | [Paddle pricing](https://www.paddle.com/pricing) |
| **RevenueCat** | **Free up to $2,500 monthly tracked revenue**, then **1% of tracked revenue** | [RevenueCat pricing](https://www.revenuecat.com/pricing/) |
| **Sentry** | **Free** Developer tier (5k errors, 5M spans, 1 user, 30-day retention); Team **$26/mo** annual | [Sentry pricing](https://sentry.io/pricing/) |
| **Apple Developer Program** | **$99/year** | [Apple Developer Program](https://developer.apple.com/programs/) |
| **Cloudflare Workers Paid** | **$5/mo minimum**, 10M requests included, $0.30/additional M | [Workers pricing](https://developers.cloudflare.com/workers/platform/pricing/) |

**Note the US$2.9k/mo asymmetry:** the standard Stripe US rate quoted in the brief (2.9% + $0.30) is the US card rate; Stripe's Austrian page publishes **1.5% + €0.25** for EEA cards. For a Prague-based developer selling into the EU, web checkout via Stripe is roughly **half the fee** the brief assumed — and one-tenth of Apple's 15%. This matters (§5.3).

### 1.5 The 30%/15% question, resolved

**VERIFIED:** the developer qualifies for the Apple Small Business Program at **15%** — the threshold is $1M in annual proceeds and a validation-stage app is nowhere near it; "developers new to the App Store also qualify." Google Play is **15%** outside EEA/UK/US and **10% + 5% billing fee = 15% effective** inside it. **All modelling below uses 15%**, not 30%. Using 30% would roughly halve every net-per-subscriber figure and double every subscriber count.

---

## 2. Usage assumptions (all ASSUMPTION — challenge these independently)

| # | Assumption | Value | Rationale |
|---|---|---|---|
| A1 | Clip length | **10 s** | Brief states 5–15 s; 10 s is the midpoint. |
| A2 | Clip file size after in-app compression | **20 MB** | **ASSUMPTION.** 1080p60 H.265 at ~16 Mbps ≈ 20 MB/10 s. A 240 fps slow-mo original can be 40 MB+; the app should transcode locally before upload. Sensitivity: 12 MB and 40 MB rows shown. |
| A3 | Clip retention | **12 months** | Athletes compare against old lifts; this is the product's retention hook. Deleting at 30 days would cut storage cost 12×, and storage is negligible anyway. |
| A4 | Replays per clip | **3 lifetime** | **ASSUMPTION.** Only matters on S3 (egress); zero cost on R2. |
| A5 | Frames actually needed for fault detection | **45** (15 fps over the 3 s that matters) | **ASSUMPTION, load-bearing.** 1 fps default (10 frames) cannot see a bar path fault. 15 fps over the pull-through-catch window is the minimum credible fidelity. |
| A6 | Text prompt (system + rubric) | **800 tokens** | **ASSUMPTION.** |
| A7 | Output tokens (narrative coaching + corrective programming) | **700 tokens** | **ASSUMPTION.** ~350 words of coaching plus a short prescription block. |
| A8 | Pose-series payload when pose runs on-device | **3,000 input tokens** | **ASSUMPTION.** 17–19 joints × ~25 keyframes, sent as summary statistics and angle series, not raw floats. Naive raw JSON of 45 frames × 19 joints × 3 floats would be ~15k tokens — 5× the cost, avoidable by design. |
| A9 | Free-tier usage | **8.7 analyses/month** (2/week) | Given in the brief. |
| A10 | Paying-subscriber usage | **8.7/month** baseline, **30/month** power-user sensitivity | **ASSUMPTION.** A serious weightlifter trains 4–6×/week and could plausibly film 2–4 lifts per session. |
| A11 | Refunds + chargebacks + involuntary churn revenue loss | **5% of gross** | **ASSUMPTION**, but anchored: RevenueCat reports involuntary billing failures are ~**31% of Google Play cancellations** and ~**14% on the App Store** ([State of Subscription Apps](https://www.revenuecat.com/state-of-subscription-apps/)). 5% is the revenue haircut, not the churn rate. |
| A12 | Free→paid conversion | **2.9%** | **VERIFIED figure, applied as an assumption.** RevenueCat's D35 download-to-paid median for **Health & Fitness is 2.9%** — the highest of any category (top quartile above 6.2%). Freemium-access-model median overall is 2.1%; hard paywalls 10.7%. Sensitivity at 1% and 5% shown. |

**One more VERIFIED figure that should worry you:** RevenueCat reports **AI apps churn 30% faster** than non-AI apps despite earning 41% more per payer ([State of Subscription Apps](https://www.revenuecat.com/state-of-subscription-apps/)). This app is an AI app in the Health & Fitness category. The 2.9% conversion is the good news; the churn multiplier is the bad news, and it lands directly on the LTV:CAC arithmetic in §7.

---

## 3. Per-analysis inference cost — the arithmetic

### 3.1 Architecture A — full cloud video LLM

Send the MP4 to Gemini; it samples frames and returns the whole analysis. Frame count is set by `fps`.

**Formula:** `cost = (frames × tokens_per_frame + prompt) × input_rate + output × output_rate`

Gemini 3 Flash Preview at $0.50/1M in, $3.00/1M out; 258 tokens/frame at standard `media_resolution`; audio disabled (no value in a snatch clip, saves 320 tokens):

| Sampling | Frames | Frame tokens | Input cost | Output cost | **Total** |
|---|---|---|---|---|---|
| 1 fps default (10 s) | 10 | 2,580 | (2,580+800)×$0.50/1M = $0.00169 | 700×$3/1M = $0.00210 | **$0.00379** |
| 1 fps, low res (66 tok) | 10 | 660 | $0.00073 | $0.00210 | **$0.00283** |
| **15 fps over 3 s (A5)** | **45** | **11,610** | **(11,610+800)×$0.50/1M = $0.00621** | **$0.00210** | **$0.00830** |
| 30 fps over 3 s | 90 | 23,220 | $0.01201 | $0.00210 | **$0.01411** |
| 30 fps over full 10 s | 300 | 77,400 | $0.03910 | $0.00210 | **$0.04120** |

Same at **Gemini 3.1 Pro** ($2.00/$12.00) — the "let's use the good model" instinct:

| Sampling | Frames | Input | Output | **Total** | vs Flash |
|---|---|---|---|---|---|
| 15 fps over 3 s | 45 | (11,610+800)×$2/1M = $0.02482 | 700×$12/1M = $0.00840 | **$0.03322** | **4.0×** |
| 30 fps over 3 s | 90 | $0.04804 | $0.00840 | **$0.05644** | **4.0×** |

At **Gemini 2.5 Flash-Lite** ($0.10/$0.40), 10 frames low-res: `(660+800)×$0.10/1M + 700×$0.40/1M` = **$0.000426**. Cheapest possible, and almost certainly not accurate enough for joint-angle faults.

**OpenAI comparison (ASSUMPTION-laden, per §1.3 caveat).** Assume ~1,100 input tokens per 512×512-ish frame:
- gpt-5-mini, 10 images: `(10×1,100+800)×$0.25/1M + 700×$2/1M` = **$0.00435**
- gpt-5-mini, **50 images** (the brief's 5 fps × 10 s): `(55,800)×$0.25/1M + $0.00140` = **$0.01535**
- gpt-5, 50 images: `(55,800)×$1.25/1M + 700×$10/1M` = **$0.07675** ← 9× the Gemini Flash equivalent. Do not do this.

### 3.2 Architecture B — on-device pose + cloud text LLM

Pose runs on the phone. `VNDetectHumanBodyPoseRequest` (Vision, iOS 14+) returns up to **19 joints** per frame entirely on-device with no network call and no per-use fee; `VNDetectHumanBodyPose3DRequest` adds 3D from iOS 17+ ([Apple Vision docs](https://developer.apple.com/documentation/vision/detecting-human-body-poses-in-images)). Marginal inference cost: **$0.00**. Only the joint series (A8: 3,000 tokens) goes to the cloud, for narrative + programming.

| Text model | Input 3,000 tok | Output 900 tok | **Total** |
|---|---|---|---|
| Gemini 2.5 Flash-Lite | $0.00030 | $0.00036 | **$0.00066** |
| **OpenAI gpt-5-mini** | **3,000×$0.25/1M = $0.00075** | **900×$2/1M = $0.00180** | **$0.00255** |
| Gemini 3 Flash | $0.00150 | $0.00270 | **$0.00420** |
| Anthropic Haiku 4.5 | $0.00300 | $0.00450 | **$0.00750** |
| Anthropic Sonnet 5 | $0.00600 | $0.00900 | **$0.01500** |

Take **gpt-5-mini at $0.00255** as the Architecture B reference. It is **3.3× cheaper than Architecture A** at equal fidelity — and A's fidelity is not obviously better, because a purpose-built pose model tracking 19 joints at 60 fps sees the bar path more precisely than a general video LLM sampling 15 fps.

**What on-device trades away** (state this honestly):
- **iOS-only for the free path.** Android needs MediaPipe Pose (Google's own, free, on-device) — a second implementation, not a second bill.
- **No bar tracking.** Vision finds *joints*, not the barbell. Bar path — the single most diagnostic snatch metric — requires your own object detector (a small YOLO-pose/CoreML model, still on-device, but you must train or source it) or a cloud vision pass. **This is the real cost of Architecture B and it is engineering time, not API spend.**
- **Old devices** run pose slowly; a 240 fps clip at 19 joints is real compute. Expect to downsample.
- **You cannot improve retroactively.** A cloud pipeline lets you re-run every historical clip against a better model; an on-device pipeline requires an app update and the user's cooperation.
- **Apple's bonus lever (VERIFIED):** SBP members with <2M first-time downloads get **Apple Foundation Models on Private Cloud Compute at no cloud API cost** ([SBP page](https://developer.apple.com/app-store/small-business-program/)). If the narrative-coaching text can be generated by Apple's models, Architecture B's marginal inference cost falls to **$0.00** and only storage remains. This is the strongest cost position available and it is worth designing towards.

### 3.3 Architecture C — cloud pose + cloud text LLM

Run MediaPipe/YOLO-pose yourself on a VPS, then the same cheap text call as B.

- Pose compute: MediaPipe Pose on CPU processes a 45-frame window in roughly 2–4 vCPU-seconds (**ASSUMPTION**; MediaPipe is free/open-source, no licence cost). A €4–5/mo 2-vCPU instance provides ~5.2M vCPU-seconds/month, i.e. **>1M analyses/month** of headroom. Marginal cost per analysis is therefore effectively **$0.0002** once the box is paid for, and the box is a fixed cost.
- Note: Hetzner Cloud's per-plan monthly prices **did not render** on [hetzner.com/cloud](https://www.hetzner.com/cloud/) and are **NOT VERIFIED**; the $5/mo figure used in fixed costs is anchored on the VERIFIED [Cloudflare Workers Paid $5/mo minimum](https://developers.cloudflare.com/workers/platform/pricing/) instead, so no unverified price enters the arithmetic.
- Total: **$0.00255 + ~$0.0002 = $0.00275** per analysis, plus a fixed compute line.

C's advantage over B: platform-independent, model-upgradeable, sees the barbell if you train for it. C's disadvantage: you now upload every clip (bandwidth, latency, privacy) and you operate GPU/CPU infrastructure.

### 3.4 Storage cost per analysis

20 MB clip (A2), 12-month retention (A3), R2 at $0.015/GB-mo:

`20/1024 GB × $0.015 × 12 = $0.003516 per clip lifetime`

| Clip size | R2, 12 mo | R2, 1 mo | S3, 1 mo | S3 + 1 replay egress | B2, 1 mo |
|---|---|---|---|---|---|
| 12 MB | $0.00211 | $0.000176 | $0.000270 | $0.001055 | $0.000081 |
| **20 MB** | **$0.00352** | $0.000293 | $0.000449 | $0.001758 | $0.000136 |
| 40 MB | $0.00703 | $0.000586 | $0.000898 | $0.003516 | $0.000271 |

**Storage is noise.** Even at 40 MB held for a year it is $0.007 — comparable to one inference call. The brief's framing ("cover video storage + AI inference costs") is right to bracket them together, but storage will never be the problem. Note the S3 row: a single replay of a 20 MB clip costs **6× more in egress than a month of R2 storage**. That is the whole argument for R2.

### 3.5 Per-analysis cost table — three architectures

| Line | **A: full cloud video LLM** | **B: on-device pose + cloud text** | **C: cloud pose + cloud text** |
|---|---|---|---|
| Pose / frame analysis | Gemini 3 Flash, 45 frames @258 tok = **$0.00830** | Apple Vision / MediaPipe on-device = **$0.00000** | MediaPipe on VPS, marginal = **$0.00020** |
| Narrative + programming text | included above | gpt-5-mini, 3k in / 900 out = **$0.00255** | **$0.00255** |
| Storage, R2, 20 MB × 12 mo | **$0.00352** | **$0.00352** | **$0.00352** |
| Egress (R2) | $0.00000 | $0.00000 | $0.00000 |
| R2 Class A/B ops (~5 per clip) | ~$0.00002 | ~$0.00002 | ~$0.00002 |
| **Total per analysis** | **$0.01182** | **$0.00607** | **$0.00627** |
| Same, worst case (Gemini Pro @30 fps / Sonnet 5 text) | **$0.05996** | **$0.01852** | **$0.01872** |
| Same, cheapest defensible | $0.00635 (Flash 1 fps) | **$0.00420** (Flash-Lite text) | $0.00440 |

**Architecture B is ~2× cheaper than A at the reference configuration and ~3× cheaper at the worst case.** But note the absolute numbers: the spread between best and worst is **$0.004 to $0.060 per analysis**. At 8.7 analyses/month that is **$0.04 to $0.52 per user per month**. Against a $9.99 subscription this is a rounding error. **Per-analysis cost cannot kill this product.** What can is the next section.

---

## 4. Free-tier abuse exposure — where freemium AI products die

Free users consume 8.7 analyses/month (A9) and generate **$0.00** revenue. The cost per 1,000 free users per month:

`1,000 users × 8.7 analyses × cost_per_analysis`

| Architecture | Cost/analysis | **Per 1,000 free users/mo** | Per 10,000 free users/mo |
|---|---|---|---|
| **A** (Gemini Flash 45f) | $0.01182 | **$102.84** | **$1,028** |
| **A worst case** (Gemini Pro 90f) | $0.05996 | **$521.65** | **$5,217** |
| **B** (on-device pose) | $0.00607 | **$52.77** | **$528** |
| **C** (VPS pose) | $0.00627 | **$54.51** | **$545** |
| **B with Apple PCC text** | ~$0.00354 (storage only) | **$30.80** | **$308** |

### 4.1 The loaded cost per paying subscriber

At the **VERIFIED 2.9% Health & Fitness conversion rate**, every paying subscriber is accompanied by:

`(1 − 0.029) / 0.029 = **33.5 non-paying users**`

Each of those 33.5 costs `8.7 × cost_per_analysis` per month. The payer's *own* usage is almost irrelevant next to this:

| Arch | Payer's own cost (8.7/mo) | **Their share of the free tier (33.5 × 8.7)** | **Loaded variable cost/payer** | Free tier as % of loaded cost |
|---|---|---|---|---|
| **A** | $0.1028 | **$3.4433** | **$3.5462** | **97.1%** |
| **A worst case** | $0.5216 | **$17.4680** | **$17.9896** | 97.1% |
| **B** | $0.0528 | **$1.7669** | **$1.8197** | **97.1%** |
| **C** | $0.0546 | $1.8252 | $1.8798 | 97.1% |

**Read that column again. 97% of your variable cost is people who will never pay you.** The paying subscriber's own inference is five cents; the 33.5 freeloaders attached to them are $1.77–$3.44. Optimising the paid path is nearly pointless; the free tier *is* the cost structure.

### 4.2 Sensitivity to conversion rate — the death scenario

Architecture A worst case (Gemini 3.1 Pro, 30 fps over 3 s, $0.05996/analysis), $9.99/mo, 15% store cut, 5% refund haircut:

| Conversion | Free users per payer | Free-tier cost per payer | Payer's own cost | Revenue after store+refunds | **Net per subscriber** |
|---|---|---|---|---|---|
| **1.0%** | 99.0 | $51.64 | $0.52 | $8.07 | **−$44.10** |
| **2.9%** (H&F median) | 33.5 | $17.47 | $0.52 | $8.07 | **−$9.92** |
| **5.0%** (top quartile) | 19.0 | $9.91 | $0.52 | $8.07 | **−$2.37** |

**Negative at every plausible conversion rate.** That architecture is not a business, it is a subsidy programme for people who don't pay. And it is exactly the architecture a developer reaches for by default: "use the best model, sample enough frames to be accurate, be generous with the free tier to drive adoption."

Same table for **Architecture B** ($0.00607):

| Conversion | Free/payer | Free-tier cost/payer | **Net per subscriber** | Subs for $1k net |
|---|---|---|---|---|
| **1.0%** | 99.0 | $5.23 | **$2.79** | **375** |
| **2.9%** | 33.5 | $1.77 | **$6.25** | **167** |
| **5.0%** | 19.0 | $1.00 | **$7.01** | **149** |

Architecture B survives even a 1% conversion rate. Architecture A-worst-case survives nothing. **This single comparison is the most important output of the whole analysis.**

### 4.3 Deliberate abuse

A determined abuser creating fresh accounts (or exploiting a client-side quota) at 10× the intended rate = 87 analyses/month:

| Arch | Cost of one abuser/month |
|---|---|
| A worst case | **$5.22** |
| A | $1.03 |
| B | $0.53 |

Individually trivial. The exposure is not one abuser but a coordinated ring or a viral moment: 10,000 free users on Architecture A worst case is **$5,217/month** of pure loss, which exceeds the entire $3k profit target by 74%. The mitigations are cheap and should ship on day one:
- **Server-side quota keyed to the App Store / Play receipt**, not to a local counter or an email address (**ASSUMPTION**: this closes ~90% of casual abuse).
- **Hard cap on paid tier too** — e.g. 60 analyses/month, above which analyses queue or degrade. See §6.
- **Rate limit per device** (Apple's `DeviceCheck`) rather than per account.
- **Architecture B makes abuse structurally cheaper** because the expensive part runs on the abuser's own phone, at the abuser's own battery expense. This is an underrated security property of on-device inference.

---

## 5. Fixed costs and the subscriber count for $1–3k/month net

### 5.1 Fixed monthly costs

| Line | Monthly | Basis |
|---|---|---|
| Apple Developer Program | **$8.25** | $99/yr ÷ 12 — [VERIFIED](https://developer.apple.com/programs/) |
| Sentry | **$0.00** at Developer tier (5k errors/mo, 1 user) → **$26.00** at Team | [VERIFIED](https://sentry.io/pricing/). Free tier is adequate below ~1k users. |
| RevenueCat | **$0.00** below $2,500 MTR, then **1% of tracked revenue** | [VERIFIED](https://www.revenuecat.com/pricing/) |
| Domain | **$1.50** | **ASSUMPTION**, ~$18/yr .com |
| Backend (Cloudflare Workers Paid) | **$5.00** | [VERIFIED $5/mo minimum, 10M requests](https://developers.cloudflare.com/workers/platform/pricing/) |
| Pose compute box (Architecture C only) | **~$5.00** | **ASSUMPTION** — Hetzner-class shared vCPU; actual Hetzner price NOT VERIFIED (§3.3) |
| **Fixed total used in model** | **$45.75** | includes Sentry Team at $26 for headroom |

Fixed costs are **negligible** — $46/month against a $1,000 target is 4.6%. The single largest "fixed" line is really variable: RevenueCat's 1% above $2,500 MTR. At $3k net you are around $4.2k gross, so RevenueCat costs ~$42/month — as much as everything else combined. **Worth noting but not worth avoiding**; hand-rolling StoreKit 2 receipt validation to save $42/month is a bad trade at this scale.

### 5.2 Waterfall: gross → net, worked example

$9.99/mo, Architecture B, 8.7 analyses/mo, 2.9% conversion:

```
Gross price                                    $9.9900
− Refunds/chargebacks/involuntary churn (5%)  −$0.4995   → $9.4905
− Apple Small Business Program (15%)          −$1.4236   → $8.0669
− Payer's own inference + storage (8.7 × $0.00607)  −$0.0528   → $8.0141
− Their share of the free tier (33.5 × 8.7 × $0.00607) −$1.7669
                                              ─────────
Net contribution per subscriber                $6.2472
```

Then: `subscribers for $1k net = ($1,000 + $45.75) / $6.2472 = **167**`

### 5.3 The table

Assumptions: 15% store commission, 5% refund/churn haircut, 2.9% conversion (33.5 free users loaded per payer), 8.7 analyses/mo, fixed costs $45.75/mo.

| Price | Arch | **Net per sub after all costs** | **Subs for $1k net** | **Subs for $3k net** |
|---|---|---|---|---|
| **$4.99** | A | $0.483 | **2,163** | **6,300** |
| **$4.99** | **B** | **$2.208** | **474** | **1,379** |
| **$9.99** | A | $4.521 | **231** | **674** |
| **$9.99** | **B** | **$6.246** | **167** | **488** |
| **$14.99** | A | $8.558 | **122** | **356** |
| **$14.99** | **B** | **$10.283** | **102** | **296** |
| **$19.99** | A | $12.596 | **83** | **242** |
| **$19.99** | **B** | **$14.321** | **73** | **213** |

**The $4.99 row is the finding.** At $4.99 on Architecture A you need **2,163 subscribers** for $1k net — because the $3.55 loaded variable cost eats 84% of the $4.24 you keep after Apple and refunds. At $9.99 on Architecture B you need **167**. That is a **13× difference in the marketing problem** for the same profit, driven entirely by two decisions (price point and architecture) that cost nothing to make correctly on day one.

**$4.99 is not viable for this product.** Not because the margin is negative, but because 474 paying subscribers in a niche as small as competitive/serious snatch practitioners is a much harder ask than 167, and the extra 307 subscribers buy you nothing.

### 5.4 Web checkout comparison (Architecture B, 8.7/mo)

Because Apple's 15% is the single biggest line item, a web-purchase path is worth quantifying. Using Stripe's published EEA rate (1.5% + €0.25 — but modelled here at the more conservative US 2.9% + $0.30 from the brief) and Paddle's 5% + $0.50:

| Price | Apple/Play 15% | **Stripe (2.9% + $0.30)** | **Paddle (5% + $0.50)** |
|---|---|---|---|
| $4.99 | $2.208 | **$2.482** | $2.182 |
| $9.99 | $6.246 | **$7.094** | $6.695 |
| $14.99 | $10.283 | **$11.707** | $11.207 |
| $19.99 | $14.321 | **$16.319** | $15.720 |

At $9.99, Stripe web checkout nets **$7.09 vs $6.25** in-app — **+13.6%**, cutting the $1k target from 167 to **147 subscribers**. Paddle nets $6.70 (+7.2%) and hands you EU VAT compliance, which at a Prague base is not optional. On Stripe's actual published Austrian EEA rate (1.5% + €0.25) the advantage is larger still.

**But:** you may not advertise the web price inside the iOS app in most jurisdictions, conversion on a web paywall is materially worse than a native StoreKit sheet (no Face ID one-tap), and you must handle VAT yourself if not using Paddle. **INFERRED conclusion:** ship in-app purchase first, add a web option later for the subset of users who arrive via content/SEO rather than App Store search. The 13% is real but it is not the lever — the free tier is.

### 5.5 What removing the free tier does

Hard paywall (no free analyses), Architecture B, $9.99. RevenueCat's VERIFIED data: hard paywalls convert at a **10.7% median vs 2.1% freemium — 5× better** — and one-year retention is "nearly identical" between the two models ([State of Subscription Apps](https://www.revenuecat.com/state-of-subscription-apps/)).

| Model | Loaded variable cost/payer | Net per sub | **Subs for $1k net** |
|---|---|---|---|
| Freemium, 2.9% conv | $1.8197 | $6.246 | **167** |
| **Hard paywall / trial-only** | **$0.0528** | **$8.014** | **130** |

Removing the free tier improves net per subscriber by **28%** *and*, per RevenueCat's own data, converts **5× better**. The freemium tier in the brief is a cost centre with no demonstrated conversion benefit. **This is the strongest recommendation in this document**: replace "2 free analyses/week forever" with **a 7-day free trial** (Health & Fitness trial-to-paid median is a VERIFIED **37.7%**) or a **one-time 3-analysis taste** that does not recur. Recurring free capacity is what creates the 33.5:1 load ratio, and nothing in the cited data says you need it.

---

## 6. Power-user sensitivity

A keen athlete filming 30 analyses/month instead of 8.7 (A10):

| Price | Arch | Net @ 8.7/mo | **Net @ 30/mo** | Δ | Subs for $1k @ 30/mo |
|---|---|---|---|---|---|
| $4.99 | A | $0.483 | **$0.232** | −52% | **4,514** |
| $4.99 | B | $2.208 | **$2.079** | −5.8% | 503 |
| $9.99 | A | $4.521 | **$4.269** | −5.6% | 245 |
| $9.99 | B | $6.246 | **$6.117** | −2.1% | 171 |
| $19.99 | B | $14.321 | **$14.192** | −0.9% | 74 |

**The power-user problem is much smaller than expected, and this is worth saying plainly because the brief anticipates the opposite.** Going from 8.7 to 30 analyses/month on Architecture B at $9.99 costs **13 cents** — a 2.1% margin hit. The reason: the loaded free-tier share ($1.77) dwarfs the payer's own usage even at 30 analyses.

The one row where it bites is **$4.99 on Architecture A**, where net per sub falls 52% and the $1k target jumps to **4,514 subscribers**. That is the "cheap price + expensive architecture" quadrant, and it is unviable regardless.

**Extreme sensitivity — where it does invert.** At Architecture A worst case ($0.05996) and 100 analyses/month (a coach analysing a whole squad through one account), the payer's own cost is **$6.00** against $8.07 of retained revenue, before any free-tier share. That breaks. Mitigation: **cap the paid tier at ~60 analyses/month** and sell a coach/team tier above it. Costs nothing to implement, removes the tail risk entirely. **INFERRED.**

---

## 7. Marketing / CAC — the assumption that undoes everything above

**Every number in §5 assumes $0 customer acquisition cost.** That is only true for organic App Store search, word of mouth in weightlifting gyms, and content marketing — all real channels for a niche this specific, and all slow.

**VERIFIED CPI benchmarks** ([Business of Apps, Cost Per Install research](https://www.businessofapps.com/ads/cpi/research/cost-per-install/)):

| Channel / geography | CPI |
|---|---|
| iOS global | **$1.50 – $3.50** |
| Android global (Google Play) | $1.50 – $4.00 |
| North America | **$2.50 – $5.00** |
| EMEA | $2.00 – $4.00 |
| Facebook Ads | $1.00 – $3.00 |
| TikTok Ads | $0.50 – $2.50 |
| Google Ads | $0.50 – $2.50 |

*(Note: this source publishes CPI by geography and by ad network, and by game genre, but **not** a Health & Fitness-specific CPI. The category figure is **NOT VERIFIED** — the iOS global range is used as the proxy, which is conservative in the sense that a highly targeted niche audience typically costs **more** per install than the blended global average, not less.)*

**Blended CAC = CPI ÷ conversion rate:**

| CPI | Conversion | **CAC per paying subscriber** |
|---|---|---|
| $2.00 | 2.9% | **$69** |
| $3.50 | 2.9% | **$121** |

**Now the LTV test.** Architecture B, $9.99, net contribution $6.25/month:

| Monthly churn | **Net LTV** | vs CAC $69 | vs CAC $121 |
|---|---|---|---|
| 8% (≈12.5-mo life) | **$78.07** | 1.13× — **fails** the 3× rule | 0.65× — **loses money** |
| 12% (≈8.3-mo life) | **$52.05** | 0.75× — **loses money** | 0.43× — **loses money badly** |

And recall the VERIFIED finding that **AI apps churn 30% faster** than non-AI apps ([RevenueCat](https://www.revenuecat.com/state-of-subscription-apps/)), which pushes you towards the 12% row, not the 8% row.

**Conclusion, stated bluntly: paid acquisition does not work for this product at $9.99.** LTV:CAC is below 1.0 at realistic churn and mid-range CPI. There is no volume of ad spend that produces $1–3k/month of profit. The paths that do work:
1. **Raise price to $19.99.** Net LTV at 8% churn becomes $14.32/0.08 = **$179** against $69 CAC = **2.6×** — borderline viable, and only 73 subscribers needed for $1k net.
2. **Organic only.** Coach partnerships, weightlifting YouTube/Instagram, r/weightlifting, competition presence. Slow, unpredictable, and the only route that keeps the §5 table honest.
3. **Annual pricing.** Collect 12 months up front (e.g. $79.99/yr), which converts an LTV problem into a cash-flow advantage and cuts involuntary churn exposure.

This CAC finding is arguably more decisive than anything in §3–§5, and it is a **demand-side** finding, not a cost-side one.

---

## 8. Summary of decisions this analysis forces

| Decision | Recommendation | Cost impact |
|---|---|---|
| Storage | **Cloudflare R2** | Zero egress; S3 egress is 6× a month of R2 storage per replay |
| Video delivery | **Plain MP4 from R2, no streaming platform** | Stream/Mux/Bunny/api.video all price per minute for long-form; ~3× R2 for no benefit at 10 s |
| Pose extraction | **On-device (Apple Vision / MediaPipe)** | $0.00 marginal vs $0.0083–$0.056 cloud; also makes abuse cheap |
| Bar-path tracking | **On-device CoreML detector** — the real engineering cost of Arch B | Engineering time, not API spend |
| Text generation | **gpt-5-mini or Gemini Flash-Lite**, on a compact joint series (3k tok, not 15k raw) | $0.0007–$0.0026 vs $0.015 on Sonnet 5 |
| Frame sampling | **Never accept Gemini's 1 fps default** if using Arch A; and never sample the full 10 s at 30 fps | 10× either way |
| Free tier | **Kill the recurring 2/week. Use a 7-day trial.** | +28% net/sub, and 5× better conversion per RevenueCat |
| Price point | **$14.99–$19.99, not $4.99** | $4.99 needs 474–2,163 subs for $1k; $19.99 needs 73–83 |
| Store commission | **Enrol in Apple SBP at 15%** — you qualify | Halves the biggest line item vs 30% |
| Paid tier cap | **~60 analyses/month**, coach tier above | Removes tail risk at zero cost |
| Paid acquisition | **Do not, at $9.99.** LTV:CAC < 1.0 | — |

---

## 9. What is NOT verified in this document

Stated explicitly so it can be challenged:

1. **Hetzner Storage Box and Hetzner Cloud monthly prices** — render client-side; did not load on [storage-box](https://www.hetzner.com/storage/storage-box/), [BX11 page](https://www.hetzner.com/storage/storage-box/bx11/), [docs](https://docs.hetzner.com/storage/storage-box/general/), or [cloud](https://www.hetzner.com/cloud/). Excluded from arithmetic rather than guessed.
2. **AWS S3 Standard $/GB-month** did not render in the [pricing page](https://aws.amazon.com/s3/pricing/) HTML; the $0.023/$0.022/$0.021 tiers were confirmed directly from the [AWS Price List API](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonS3/current/index.json) (SKU `WP9ANXZGBYYSGJEA`, `TimedStorage-ByteHrs`, US East N. Virginia). Egress $0.09/GB is the Ireland example rate stated on the page, not a US-East rate.
3. **OpenAI per-image token count** — no flat rate is published; ~1,100 tokens/image is an ASSUMPTION and every OpenAI vision figure inherits that uncertainty.
4. **Health & Fitness-specific CPI** — not published by the cited source; iOS global $1.50–$3.50 used as a proxy.
5. **Monthly churn rate** — not published in the RevenueCat excerpt reached; 8% and 12% are ASSUMPTIONS, informed only by the VERIFIED "AI apps churn 30% faster" finding.
6. **Clip file size (20 MB), pose payload (3k tok), MediaPipe vCPU-seconds, replay count, retention period** — all ASSUMPTIONS, each independently challengeable, with sensitivity ranges shown where they matter.
7. **Google Cloud Storage** rates did not render and are omitted entirely.

---

## Verdict impact

**Neutral on cost; the analysis supports NO-GO on the pricing and free-tier design as briefed, and shifts the entire verdict question onto demand.**

**Cost is not the binding constraint.** Per-analysis cost is $0.006–$0.012 under any sane architecture — 0.06% to 0.12% of a $9.99 subscription. Storage is $0.0035 per clip-year and will never matter. If the question is "can this app cover its storage and inference costs?", the answer is yes, trivially, by two orders of magnitude. On that narrow reading of the success bar, this supports **GO**.

**But the success bar has a second clause — "net $1–3k/month profit" — and that clause is demand-bound, not cost-bound.** The binding constraints, in order:

1. **Demand.** You need **167 paying subscribers at $9.99** (Arch B) or **73 at $19.99** for $1k/month net; **488** or **213** respectively for $3k. Whether a serious-snatch-practitioner niche yields that many payers is the real question, and it is not a question this document can answer — it belongs to the demand-evidence ticket. Nothing about cost prevents it; nothing about cost helps it either.
2. **The free tier as briefed.** "2 analyses/week free forever" loads **33.5 non-paying users onto every payer** at the VERIFIED 2.9% Health & Fitness conversion rate, making **97% of variable cost attributable to people who never pay**. On the naive architecture (Gemini Pro, dense frame sampling) at 1% conversion this produces **−$44 net per subscriber** — the product loses money on every single sale. This is a design defect, not a cost problem, and it is fully fixable before launch: a 7-day trial converts **5× better** per RevenueCat's own data and improves net per subscriber by 28%.
3. **CAC.** At the VERIFIED iOS CPI range of $1.50–$3.50 and 2.9% conversion, blended CAC is **$69–$121** against a net LTV of **$52–$78** at $9.99. **LTV:CAC is below 1.0.** Paid acquisition cannot fund this business at $9.99. This forces either $19.99 pricing (LTV:CAC ≈ 2.6× at 8% churn) or a purely organic growth strategy — and the VERIFIED finding that AI apps churn 30% faster pushes towards the pessimistic end.

**The one architectural decision that decides everything** is on-device pose extraction (Architecture B): $0.00 marginal inference, 2–3× cheaper loaded cost, structurally abuse-resistant, and with Apple's VERIFIED Private Cloud Compute perk for SBP members under 2M downloads it can reach near-zero marginal cost entirely. It survives a 1% conversion rate. The full-cloud-video-LLM alternative does not survive any conversion rate at high fidelity. **Choose B, price at $14.99–$19.99, replace the recurring free tier with a trial, and cost ceases to be a topic of conversation — at which point the whole verdict rests on whether the demand exists.**
