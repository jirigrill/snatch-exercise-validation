# 01 — Market sizing: addressable athletes and willingness to pay
Ticket: [#1](https://github.com/jirigrill/snatch-exercise-validation/issues/1) · Status: resolved · Date: 2026-09-14

All prices and population figures below were retrieved on **2026-09-14** and carry source links. Every non-obvious claim is tagged **VERIFIED** / **SECONDARY** / **INFERRED** / **ASSUMPTION** / **NO EVIDENCE FOUND**.

> Tooling note: the general web-search API was unavailable during this research. Findings were gathered by direct page fetches plus a search proxy. Two intended figures (USA Weightlifting current membership, British Weight Lifting membership) could not be confirmed from primary sources — see section 3.

## Headline

The addressable market is real but small, and it is **shrinking, not growing**. The hard proxy for competitive hobbyists — CrossFit Open registrations — fell from ~350,000 (2024) to 234,000 (2025), a >30% single-year collapse, and CrossFit affiliates are down ~34% from their 2018 peak with the parent company unsold and in open financial distress. Worse for this specific product: the "AI barbell form analysis" niche is **already occupied by at least eight shipping apps**, several free or under $8/month, which caps price rather than leaving room for it. The arithmetic below lands on a realistic paying base of roughly **250–600 subscribers**, which does clear a $1–3k/month profit bar — but only at the optimistic end, and only if the app wins a meaningful share of a niche that incumbents already price near zero.

## 1. CrossFit population and the Open as a hobbyist proxy

The CrossFit Open is the single best hard proxy for "athlete who already knows the movement and cares enough to be measured." It requires paid registration and deliberate effort, so it filters out casual gym-goers.

| Year | Open registrations | Note |
|---|---|---|
| 2011 | 26,000 | first Open |
| 2012 | 69,000 | |
| 2014 | 209,585 | |
| 2018 | 415,000 | **peak** |
| 2020 | 239,106 | format change + rescheduling |
| 2023 | ~323,000 | |
| 2024 | ~350,000 | recent local high |
| 2025 | **234,000** | **down >30% YoY** |

**VERIFIED** — all of the above from [Wikipedia: CrossFit Games](https://en.wikipedia.org/wiki/CrossFit_Games), which cites CrossFit's own "209,585: Rise of the Open" for 2014. The 2024→2025 drop is independently corroborated at "-31% year-over-year" **SECONDARY** ([The Collapse of CrossFit](https://www.patreon.com/thesurgeonsroadie/posts/collapse-of-case-146455266)).

Affiliate gym counts — the distribution channel and the place snatching is actually coached:

| Point in time | Affiliates | Note |
|---|---|---|
| 2005 | 13 | |
| 2013 | 8,000 | |
| 2016 | 13,000+ | |
| 2018 | ~15,500 in 162 countries | **peak** |
| Early 2021 | 9,400 paying | post-Glassman disaffiliations + COVID |
| Early 2022 | 10,800 paying (~12,500 incl. non-paying) | |
| 2024 | ~11,400 paying | |
| March 2025 | **9,899 active** | lowest since mid-2010s |
| 2026 | ~9,300 (projection only) | **INFERRED/third-party projection, not actual** |

**VERIFIED** — 2005–2025 figures from [Wikipedia: CrossFit](https://en.wikipedia.org/wiki/CrossFit). The precise March 2025 count of 9,899 and the -13% twelve-month decline are **SECONDARY** ([Fitness Avenue, 2026](https://www.fitnessavenue.ca/blogs/post/how-many-crossfit-gyms-are-there-2026-data-by-country)), which also puts the US at ~5,000 affiliates (about half the world total) and Canada third at 600+. The 2026–2028 projections in that source are that publisher's extrapolation and should not be treated as data.

Over 1,400 gyms de-affiliated in 2024 alone, 857 of them after the 2024 Games, attributed to the affiliate fee rising from $3,000 to $4,500 and to the athlete death at that event **VERIFIED** ([Wikipedia: CrossFit Games](https://en.wikipedia.org/wiki/CrossFit_Games)).

Total worldwide CrossFit *membership* is estimated at **2–5 million** **SECONDARY** ([Wikipedia: CrossFit](https://en.wikipedia.org/wiki/CrossFit)) — a range so wide (2.5x) that it is nearly useless for sizing. The Open number is the more honest denominator.

## 2. CrossFit HQ instability — is this market growing or shrinking?

Shrinking, and the parent company is in visible distress. This matters because affiliate gyms are both the coaching context in which snatching is learned and the most plausible distribution channel for the app.

| Fact | Tag | Source |
|---|---|---|
| CrossFit put itself up for sale (2nd time since 2020), announced March 2025 | **VERIFIED** | [CrossFit's Next Chapter](https://www.crossfit.com/announcements/crossfits-next-chapter-an-update-to-our-community) — "It is now time to seek out a new owner" |
| Sale framed around "an athlete death and financial concerns" | **SECONDARY** | [NYTimes DealBook, 2025-03-13](https://www.nytimes.com/2025/03/13/business/dealbook/crossfit-for-sale.html) |
| Sale characterised as following "years of drama and attrition" | **SECONDARY** | [Front Office Sports, 2025-03-14](https://frontofficesports.com/crossfit-for-sale-after-years-of-drama-and-attrition/) |
| **Still unsold as of January 2026** — no transaction announced | **SECONDARY** | [Hybrid Fitness Media, 2026-01-08](https://hybridfitnessmedia.com/2026/01/08/crossfit-not-sold-deal-status-january-2026/) |
| Exclusivity timelines passed without filings; process stalled | **SECONDARY** | [Prism Media, 2026-01-15](https://prismedia.ai/news/crossfit-sale-stalled-as-exclusivity-timelines-pass-without-filings) |
| Affiliate owners cite "perceived instability at HQ" as a top-5 risk for 2026 | **SECONDARY** | [The Barbell Spin, 2026-01-20](https://www.thebarbellspin.com) |
| Affiliate fees raised ~30% between 2019 and 2022, then sharply again in 2024 | **SECONDARY** | [Fitness Avenue](https://www.fitnessavenue.ca/blogs/post/how-many-crossfit-gyms-are-there-2026-data-by-country) |
| HQ layoff figures | **NO EVIDENCE FOUND** | — |

**INFERRED:** a market whose flagship participation event lost a third of its entrants in one year, whose gym count is down 34% from peak, and whose owner has been unable to find a buyer in ~10 months of trying is a market to build *into* only with a very cheap, very fast experiment. It is not a market where a rising tide will rescue weak conversion.

## 3. Olympic weightlifting federation membership

This is where the research is weakest, and I am flagging it rather than filling it with a guess.

| Body | Figure | Tag | Source |
|---|---|---|---|
| USA Weightlifting | ~30,000 members, up from 9,000 pre-COVID (as of Aug 2021) | **SECONDARY**, and **five years stale** | [Forbes, 2021-08-03](https://www.forbes.com/sites/michellebruton/2021/08/03/ceo-phil-andrews-made-usa-weightlifting-into-an-olympic-contender-now-he-wants-to-clean-up-the-sport-globally/) |
| USA Weightlifting, current (2025/2026) | — | **NO EVIDENCE FOUND** — usaweightlifting.org gives only "one of the fastest growing sports in America" with no numbers; no annual-report page reachable (404) | [usaweightlifting.org](https://www.usaweightlifting.org/) |
| USAW National Championships 2026 field | "over 1,500 athletes" across 8 days | **VERIFIED** | [usaweightlifting.org](https://www.usaweightlifting.org/) |
| USAW Local Weightlifting Committees | 45 state-oriented LWCs | **VERIFIED** | [Wikipedia: USA Weightlifting](https://en.wikipedia.org/wiki/USA_Weightlifting) |
| British Weight Lifting | "thousands of people actively involved" — no count published | **NO EVIDENCE FOUND** | [Wikipedia: British Weight Lifting](https://en.wikipedia.org/wiki/British_Weight_Lifting) |
| IWF / other national federation membership | — | **NO EVIDENCE FOUND** | — |

**ASSUMPTION** (needed for the funnel, unverifiable): USAW membership today is **25,000–35,000**. The 2021 figure of 30,000 is the only hard anchor; I assume roughly flat, since the post-2021 CrossFit contraction plausibly offset organic growth. This is the single least defensible number in the document — if the real figure is 15,000, the weightlifting-side contribution to the funnel halves.

**INFERRED:** the dedicated Olympic-weightlifting population is roughly an order of magnitude smaller than the CrossFit competitive-hobbyist population (tens of thousands vs. hundreds of thousands). CrossFit is therefore the primary market and weightlifting federations are a secondary, higher-intent sliver — but note the inversion: the federation lifter snatches far more often and cares far more, so per-user willingness to pay is higher even though the population is tiny.

## 4. Who actually snatches, and cares enough to pay?

The snatch is a mandatory CrossFit Open movement in most years and a core affiliate-class lift, so exposure among Open registrants is effectively universal. Frequency and *investment* are the real filters.

| Filter step | Basis | Tag |
|---|---|---|
| Snatches at least weekly | Open registrants train in affiliates programming Olympic lifts regularly; but many boxes program the snatch in cycles, not weekly | **ASSUMPTION** — no participation-frequency survey found |
| Cares about technical perfection (vs. just completing the workout) | The persona is explicitly the self-improving hobbyist; Open registration is itself a proxy for competitive intent | **INFERRED** |
| Already pays for training content | Programming subscriptions at $19–50/mo are a mass product in this niche (section 5), so a paying habit demonstrably exists | **VERIFIED** by the existence and pricing of those products |
| Would pay *separately* for single-lift analysis on top of programming | This is the crux, and there is no direct evidence for it | **NO EVIDENCE FOUND** |

**INFERRED, and this is the central strategic risk:** the target user is already spending $20–50/month on programming. A snatch-only analysis tool is an *additional* line item competing for the same discretionary fitness budget, not a replacement for anything. Products that occupy an add-on slot rather than a primary slot convert worse and churn faster. Section 6 shows the market has already pushed this exact category toward free.

## 5. Willingness to pay: published benchmarks

### 5a. Programming subscriptions (the closest comparable — same buyer, same budget)

All **VERIFIED** from the linked retailer or vendor page unless noted.

| Product | Tier | Price (USD) | Source |
|---|---|---|---|
| Mayhem Athlete | Everyday Athlete | **$19.99/mo** | [Rogue Fitness](https://www.roguefitness.com/mayhem-athlete-everyday-athlete-subscription) |
| Mayhem Athlete | Competitor | **$49.95/mo** | [Rogue Fitness](https://www.roguefitness.com/mayhem-athlete-competitor-subscription) |
| Mayhem Athlete | Affiliate (gym-wide) | $129/mo | [PushPress](https://www.pushpress.com/partners/mayhem) |
| PRVN Fitness | PRVN GO | **$25/mo** | **SECONDARY** (aggregated listings) |
| PRVN Fitness | Compete | **$39.99/mo** | [Rogue Fitness](https://www.roguefitness.com/prvn-compete-subscription) |
| PRVN Fitness | SIXTY / Age Group | ~$40/mo | **SECONDARY** |
| PRVN Fitness | HYROX | ~$45/mo | **SECONDARY** |
| PRVN Fitness | Affiliate | $122–150/mo | [Rogue](https://www.roguefitness.com/prvn-affiliate-subscription), [PushPress](https://www.pushpress.com/partners/prvn) |
| JuggernautAI | Monthly | **$34.99/mo** | [juggernautai.app](https://www.juggernautai.app/) |
| JuggernautAI | Yearly | **$349.99/yr** (~$29.17/mo) | [juggernautai.app](https://www.juggernautai.app/) |
| Catalyst Athletics | Club 5 (via TrainHeroic) | $39/mo | [TrainHeroic Marketplace](https://marketplace.trainheroic.com/) |
| Catalyst Athletics | one-time programs | $29–$199 one-off | [catalystathletics.com](https://www.catalystathletics.com/programs/) |
| TrainHeroic marketplace | typical range | **$16–$49/mo**, clustered high-$20s to $30s | [marketplace.trainheroic.com](https://marketplace.trainheroic.com/) |
| Squat University | subscription | **NO EVIDENCE FOUND** — books/seminars/clinic only, no subscription tier published | [squatuniversity.com](https://squatuniversity.com/) |
| Training Think Tank | programming/coaching | **NO EVIDENCE FOUND** — no prices published on programs or remote-coaching pages; contact-gated | [trainingthinktank.com](https://www.trainingthinktank.com/) |

**VERIFIED conclusion:** the established ceiling for *self-serve programming content* aimed at this exact buyer is roughly **$20–50/month**, with the marketplace mode near **$29–35/month**. Note these products deliver a full training week, every week — far more perceived value than one lift's analysis.

### 5b. Human remote coaching (the premium anchor)

| Segment | Price (USD/mo) | Tag | Source |
|---|---|---|---|
| Template/app programming | $10–50 | **SECONDARY** | [Coachway](https://coachway.io/articles/how-much-does-an-online-fitness-coach-cost/) |
| App programming (broader) | $50–150 | **SECONDARY** | [369MMAFIT](https://369mmafit.com/en/blog/online-personal-training-cost-2026-pricing-guide) |
| Custom async 1:1 coaching | **$100–300+** | **SECONDARY** | [Coachway](https://coachway.io/articles/how-much-does-an-online-fitness-coach-cost/) |
| Standard online-coaching package | $150–300 | **SECONDARY** | [FitBudd](https://www.fitbudd.com/post/how-to-price-your-online-fitness-coaching-services) |
| Reported "sweet spot" | $175–350 | **SECONDARY** | [WarriorBabe](https://www.warriorbabe.com/read/average-cost-of-online-personal-trainer-per-month) |
| Premium 1:1 / live video | $300–1,000+ | **SECONDARY** | [Unleashd](https://unleashdstrength.com/fitness/online-personal-training-cost/), [369MMAFIT](https://369mmafit.com/en/blog/online-personal-training-cost-2026-pricing-guide) |
| **Coach tiers that include form review** | reaching **~$400** | **SECONDARY** | [Coachway](https://coachway.io/articles/how-much-does-an-online-fitness-coach-cost/) |
| Lifter-reported actuals (powerlifting/weightlifting) | £60, $100, $180, $200, ~$220 | **SECONDARY**, self-reported | r/powerlifting, r/weightlifting threads via search results |

The $100–300/mo figure in the brief is confirmed. **INFERRED:** the fact that human coaches bundle form review into $200–400/mo packages is a double-edged signal — it proves form feedback is valued, but it also means the *substitute* for this app is a human who also writes the program, answers questions, and carries accountability. An app replaces the cheapest, most commoditised slice of that bundle.

### 5c. General fitness-app price points

| Benchmark | Value | Tag | Source |
|---|---|---|---|
| Health & Fitness median monthly price (premium tier) | **$9.99** | **VERIFIED** | [RevenueCat State of Subscription Apps](https://www.revenuecat.com/state-of-subscription-apps/) |
| H&F median weekly price | $4.99 | **VERIFIED** | same |
| H&F median yearly price | ~$39.94 | **VERIFIED** | same |
| H&F annual-plan adoption | 68% (highest of any category); 59% of category revenue | **VERIFIED** | same |

**This is the most important pricing fact in the document.** The category median monthly price is **$9.99**, not $20–50. The programming subscriptions in 5a are priced above the app-store norm because they are content businesses with named-athlete brands. A solo indie utility app will be benchmarked by users against the $9.99 median, and against free competitors (section 6).

## 6. The niche is already occupied — and priced near zero

This was not in the brief's question list, but it directly determines willingness to pay and cannot be omitted.

| App | Price | Relevance to snatch analysis | Tag |
|---|---|---|---|
| "Olympic Weightlifting AI" | **$19.99/mo**, computer-vision scoring of snatch technique | direct competitor | **SECONDARY** (search-summary attribution, no vendor page confirmed) |
| [Lift AiK](https://apps.apple.com/us/app/lift-aik/id6741048318) | not stated | tracks barbell trajectory, velocity, posture for **clean, snatch, jerk** | **VERIFIED** listing exists |
| [Lift App – AI Barbell Tracker](https://apps.apple.com/us/app/lift-app-ai-barbell-tracker/id6756862700) | 7-day free trial | AI barbell tracking | **VERIFIED** listing exists |
| [AI Barbell Lifting (MasisoAI)](https://apps.apple.com/us/app/ai-barbell-lifting/id1590255838) | **free**, rated 4.3 | direct competitor | **VERIFIED** listing exists |
| [Weightlifting.ai](https://www.weightlifting.ai/) | not stated | Olympic-lift specific | **VERIFIED** site exists |
| [FormVision](https://www.formvision.app/) | "first analysis free" — same freemium hook as the product under test | direct competitor | **SECONDARY** |
| [Gymscore](https://www.gymscore.ai/) | not stated | scores form 0–100 | **SECONDARY** |
| [FormChecker](https://www.formchecker.ai/) | not stated | form checking | **SECONDARY** |
| [Freeletics AI Coach](https://kensoforge.com/insights/ai-form-checker-computer-vision-lifting-apps-2026) | free, premium **$7.99/mo** | phone-camera form analysis | **SECONDARY** |
| Tempo Studio | $2,495 hardware + $39/mo | most advanced barbell CV, but hardware-gated | **SECONDARY** |

**VERIFIED (as a set):** at least eight shipping apps already do AI barbell/form analysis, several explicitly naming the snatch, at least one free, and the software-only field priced under $8–20/month ([Kenso Forge roundup, 2026](https://kensoforge.com/insights/ai-form-checker-computer-vision-lifting-apps-2026)).

**INFERRED:** the product under test has no pricing headroom above ~$10–15/month and no defensible novelty in "overlay + AI narrative." FormVision already runs the identical freemium hook (first analysis free). The differentiators that remain are snatch-specific depth and the AI-generated corrective programming — neither of which is verified as a purchase driver by anything found here.

## 7. Realistic conversion: what a solo indie app actually captures

RevenueCat's *State of Subscription Apps* is the best available public benchmark. All **VERIFIED** from [revenuecat.com/state-of-subscription-apps](https://www.revenuecat.com/state-of-subscription-apps/).

| Metric | All categories | Health & Fitness |
|---|---|---|
| Apps reaching **$1,000/mo** revenue | **17.3%** | not broken out |
| Apps reaching **$10,000/mo** revenue | **4.6%** | not broken out |
| Median days to $1k / $10k | 58 / 109 | ">100 days to >$10k" (contributor note) |
| Median monthly revenue 1 yr post-launch | ~$72 | not listed |
| Download→trial (D30) | — | 6.9% (2nd best; top performers >23%) |
| Trial→paid | — | 37.7% (2nd best; upper quartile >51.4%) |
| **D35 download→paid** | — | **2.9% — highest of any category** (upper quartile >6.2%) |
| Revenue per install (D60) | $0.34 | **$0.66 — leads all categories** |
| RLTV per payer, year 1 | — | **$35.64 median** (category leader) |

**Correction to the brief's premise, and it cuts in the product's favour:** the brief states Health & Fitness is "one of the WORST categories for revenue milestones." The report does **not** support that. H&F was not broken out for the $1k/$10k milestone rates, and on every metric where it *is* itemised it is at or near the **top**: best D35 download-to-paid (2.9%), best revenue per install ($0.66 at D60), best RLTV per payer ($35.64 year 1), second-best trial-to-paid. **VERIFIED.** The one negative signal is a contributor remark that H&F needs >100 days to exceed $10k/mo.

**The genuinely sobering numbers are the all-category ones:** only **17.3%** of subscription apps ever reach $1,000/month, only **4.6%** reach $10,000/month, and the median app makes **~$72/month** a year after launch. **VERIFIED.**

**Critical caveat, INFERRED:** RLTV of $35.64 per payer in year 1 is a *lifetime* figure, not monthly. At the $9.99 category median that implies the median payer churns after roughly 3.5 months. A funnel built on monthly-subscriber counts must be read as "subscribers at a point in time, being continuously replaced," not as a stable annuity.

## 8. The funnel: from population to paying subscribers

Starting from the hardest verifiable number (2025 Open registrations) rather than the 2–5M membership guess, then adding the federation lifters.

| Step | Multiplier | Remaining | Tag & basis |
|---|---|---|---|
| CrossFit Open 2025 registrants | — | **234,000** | **VERIFIED** ([Wikipedia](https://en.wikipedia.org/wiki/CrossFit_Games)) |
| + USAW members not already counted | +25,000 | **259,000** | **ASSUMPTION** — 2021 Forbes anchor of ~30,000, assumed flat, minus overlap with CrossFit |
| + non-US federation lifters (BWL, others) | +20,000 | **279,000** | **ASSUMPTION** — **NO EVIDENCE FOUND** for any national federation count; pure estimate |
| English-language capable | ×0.65 | 181,000 | **ASSUMPTION** — US ~50% of affiliates plus UK/CAN/AUS/IRL and high English proficiency in N. Europe |
| Snatches regularly enough to want repeat analysis | ×0.60 | 109,000 | **ASSUMPTION** — many boxes program the snatch in cycles, not weekly; no frequency survey found |
| Cares about technical perfection (persona fit: not a beginner, actively self-improving) | ×0.40 | 43,500 | **ASSUMPTION** |
| Smartphone owner willing to film themselves lifting in a public gym | ×0.70 | 30,500 | **ASSUMPTION** — filming friction is real and under-modelled; this may be generous |
| **= Serviceable addressable market (SAM)** | | **~30,000** | **INFERRED** from the above |
| Will ever discover/install the app (solo indie, no marketing budget, 8+ incumbents competing for the same keywords) | ×0.10 | 3,050 installs | **ASSUMPTION** — a solo dev reaching 10% of a global niche is already a strong outcome |
| Install → paid (H&F D35 median 2.9%; upper quartile 6.2%) | ×0.029 → ×0.062 | **88 – 189 payers** | **VERIFIED** rate ([RevenueCat](https://www.revenuecat.com/state-of-subscription-apps/)), applied by me |

### Revenue at the base case

| Scenario | Reach | Payers | Price | Gross MRR | Tag |
|---|---|---|---|---|---|
| Pessimistic | 5% of SAM (1,525 installs), median conversion | **44** | $9.99 | **~$440** | **INFERRED** |
| Base | 10% of SAM (3,050), median conversion | **88** | $9.99 | **~$880** | **INFERRED** |
| Base, upper-quartile conversion | 10% of SAM | **189** | $9.99 | **~$1,890** | **INFERRED** |
| Optimistic | 20% of SAM (6,100), upper-quartile conversion | **378** | $14.99 | **~$5,670** | **INFERRED** |
| Required for $1–3k net profit | — | **~250–600** | $9.99–14.99 | $2,500–6,000 gross | **INFERRED**, assumes ~40–50% of gross lost to app-store fees (15–30%), storage and inference |

**The bar: 250–600 concurrent paying subscribers.** Against a SAM of ~30,000 that is a **0.8%–2.0% penetration of the entire global serviceable niche** — which sounds achievable until you note it requires beating the base case by 3–7x, and that only 17.3% of all subscription apps ever clear even $1,000/month gross **VERIFIED**.

**Churn reality check, INFERRED:** at a median H&F year-1 RLTV of $35.64/payer, holding 400 concurrent subscribers means acquiring roughly 100+ *new* payers every month forever to replace churn. For a solo operator with no paid acquisition, that is the binding constraint — not the size of the market.

### Sensitivity: what breaks the model

| If this changes | Effect | Tag |
|---|---|---|
| Filming-in-public friction is ×0.4 not ×0.7 | SAM → ~17,000; base case halves | **INFERRED** |
| Price must drop to $4.99 to beat free competitors | payer count needed roughly doubles to 500–1,200 | **INFERRED** |
| CrossFit Open keeps falling ~30%/yr | SAM shrinks ~25%/yr; 2027 SAM ~22,000 | **INFERRED** — extrapolating one data point, weak |
| Users will pay programming-tier prices ($29–35) because corrective programming is included | 250–600 target drops to ~100–200 payers — **the single most valuable thing to test** | **INFERRED** |

## Verdict impact

**Neutral, leaning NO-GO — and the decisive risks are not market size.**

Market size alone does not kill this. A ~30,000-person SAM and a 250–600-subscriber bar is a **0.8–2.0% penetration requirement**, which is not absurd for a well-targeted niche tool, and Health & Fitness is genuinely a *strong* subscription category on conversion and revenue-per-install — the brief's premise that it is one of the worst was not supported by the RevenueCat data. **VERIFIED.**

Three findings argue against, in order of severity:

1. **Pricing headroom is already destroyed.** At least eight AI barbell-form apps ship today, one free, the software-only field at $8–20/month, and the H&F category median is $9.99. FormVision already runs the identical "first analysis free" hook. The $20–50/month that Mayhem, PRVN and JuggernautAI command is for *full weekly programming from a named brand*, not one lift's analysis — that comparison is not available to this product. **VERIFIED / INFERRED.**
2. **The market is contracting fast.** Open registrations -30% in one year, affiliates -34% from peak and -13% in twelve months, CrossFit LLC unsold after ~10 months on the market. Every year of delay makes the denominator smaller. **VERIFIED / SECONDARY.**
3. **It is an add-on purchase, not a primary one.** The target athlete already pays $20–50/month for programming. Nothing found here evidences willingness to pay *separately* for single-lift analysis — that is a **NO EVIDENCE FOUND**, and it is the load-bearing assumption of the whole business case.

What would move this to GO: evidence that the **AI-generated corrective programming** (not the overlay, which is commoditised) supports a $29–35/month price against programming subscriptions rather than a $9.99 price against form-check apps. That single question is worth more than any further market sizing, because it cuts the required subscriber count by roughly 60%.

Weakest links in this analysis, stated so they can be attacked: current USA Weightlifting membership is unverified (2021 figure used), no national federation counts were obtainable at all, no snatch-frequency survey exists, and every funnel decay step from "English-language capable" downward is my assumption rather than sourced data.
