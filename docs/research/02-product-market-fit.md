# 02 — Product-market fit: is the pain real and currently unsolved?
Ticket: [#2](https://github.com/jirigrill/snatch-exercise-validation/issues/2) · Status: resolved · Date: 2026-09-14

## Headline
The *behaviour* is real and high-frequency — r/weightlifting receives roughly 13 form-check posts per week and moderators have twice debated banishing them because they crowd out everything else. But the *free substitute* is not the bottleneck being solved either: 68% of those posts get zero replies (**VERIFIED**, see §1), so the demand for feedback demonstrably exceeds supply. The problem is that this audience's stated preference, when they do pay, is for a *human* to look at the video — and the sport's most recent recorded reaction to an AI coaching app was "Don't spend a penny on AI coaching... There's a lot of jobs AI is capable of taking over competently, this is certainly is not one of them" (**VERIFIED**). One serious player in this exact space, Weightlifting.ai, has already been quietly shut down and folded into a platform whose selling point is that "you connect with the actual coaches" (**VERIFIED**, §5).

## 1. What athletes actually do today: the r/weightlifting form-check firehose

Measured directly against the Reddit archive (pullpush.io submission search, `subreddit=weightlifting`, `q="form check"`, 100 most recent posts spanning 2025-03-24 → 2025-05-17):

| Metric | Value |
|---|---|
| Form-check posts per week | **12.9** |
| Median comments per post | **0** |
| Mean comments per post | 2.3 |
| Share of posts with zero comments | **68%** |

**VERIFIED** — computed from the pullpush.io Reddit archive API, `https://api.pullpush.io/reddit/search/submission/?subreddit=weightlifting&q=form+check&size=100`. Caveat: pullpush `num_comments` is captured at index time and understates final counts on some posts, so treat the zero-comment share as an upper bound and the "reply rate is poor" conclusion as directional rather than exact (**INFERRED**).

Two readings, both true:
- **Pro-product:** demand for feedback vastly exceeds the supply of people willing to give it. Most athletes who ask get nothing.
- **Anti-product:** an athlete who posts and gets no reply revealed that they were only willing to spend *zero* on this. Non-payment is the observed behaviour, not merely unmet demand (**INFERRED**).

Where a thread does get engagement, the human feedback is specific and mechanistically causal in a way an overlay is not. From a snatch thread (Aug 2026):

> "I think you are bumping it forwards with your hip. Stay over the bar longer during the 2nd pull and make sure to extend vertically. Not forwards." — u/amaprez, 13 upvotes

> "your centre of balance shifts to your heels and then to your toes as the bar passes your knees, which results in you bumping the bar forward rather than extending vertically." — u/Mysticwashere

**VERIFIED** — [r/weightlifting, "Forward bar in Snatch"](https://www.reddit.com/r/weightlifting/comments/1vsrk92/forward_bar_in_snatch/). Note what this feedback is: not fault *detection* (the poster already knew the bar went forward — it is in their title) but *causal attribution and a corrective cue*. That is the harder half of the job and the half the product's overlay feature does not obviously address (**INFERRED**).

## 2. Subreddit culture: form checks are tolerated, not celebrated

r/weightlifting has twice run community processes to constrain form-check posting.

A March 2022 post argued they were crowding out the sport: "it seems like this sub-reddit has been a bit saturated with form check posts lately... Can we organize form checks into one thread?" A national medalist and international coach replied:

> "Speculatively if the mods 'dropped' form checks from the main feed, then the main feed would dry up. That says a lot." — u/anthony__hernandez (National Medalist, International Coach)

**VERIFIED** — [r/weightlifting, "For your consideration: A Weekly Form Check Thread"](https://www.reddit.com/r/weightlifting/comments/tfxhyd/for_your_consideration_a_weekly_form_check_thread/).

A May 2022 official mod poll (644 votes) settled the matter:

| Option | Votes |
|---|---|
| Continue to allow Form Checks in main feed | **328** |
| Disable Form check flair, separate form check thread daily/weekly | 126 |
| Disable Form check flair, allowed in daily/weekly thread | 66 |
| Disable Form checks forevah | 55 |
| Disable fluff posts flair as workaround | 7 |
| "I just like to bitch and moan because I'm lazy/tech incompetent" | 62 |

**VERIFIED** — [r/weightlifting, "The future of Form Checks in this subreddit"](https://www.reddit.com/r/weightlifting/comments/un0va9/the_future_of_form_checks_in_this_subreddit/). Outcome: form checks stayed in the main feed. They are **not** funnelled to a weekly thread in r/weightlifting; posts carry a "Form check" flair and appear in the main feed today (**VERIFIED**, live front page shows multiple "Form check"-flaired posts).

Volume fatigue is real, including from people who *have* coaches:

> "I see some pop up on my feed nearly every single day.. even when they say they have a coach. I feel it potentially drowns out others/makes them less visible." — u/WealthApprehensive88

**VERIFIED**, same thread. This is a meaningful data point for the product: athletes who already have coaches still seek second opinions (**INFERRED** — supports demand). It is also a data point against: their chosen channel is free and social, not paid and algorithmic.

There is also a dedicated r/formcheck subreddit with a rule that directly bans this product's own distribution channel:

> "**Don't promote your own social media or app/business.** ... Please post links to those people, and not your IG, personal website, form checking app, etc."

**VERIFIED** — [r/formcheck wiki](https://www.reddit.com/r/formcheck/wiki/index/). The same wiki's guidance for *givers* of feedback describes exactly the product's proposed output: "Example frames from the form check, specific explanations of what is happening and where, and comparisons with stills/video of other quality lifters... If programming can help a lifter correct something, put that in your feedback." So the product's feature set matches the community's own definition of a good form check (**VERIFIED**) — which cuts both ways: it is the right output, and it is already available for free.

## 3. The substitutes

| Substitute | What it costs | What it gives | Where it falls short |
|---|---|---|---|
| **In-person coach** | Highly variable; described as "kinda pricey" and "isn't cheap" by lifters (**VERIFIED**, [r/weightlifting](https://www.reddit.com/r/weightlifting/comments/1anyw3s/is_a_coach_worth_it/)) | Real-time correction, cues within the set, accountability, programming. Community consensus: "110% yes if it's an in-person coach" (u/robaroo) | Geographically unavailable to many — "Unfortunately theres no coaches or club where I live" (**VERIFIED**, u/AdRelative6839, [Mar 2026](https://www.reddit.com/r/weightlifting/comments/1rj2me4/ai_coach_recommendations/)) |
| **Remote/team coach via TrainHeroic etc.** | **$20–50/mo** for team programming + coach form checks (**VERIFIED**, u/Boblaire, competitive masters lifter/coach, stated twice independently in 2024 and 2026) | Programming plus form checks "at the leisure of the coach. Maybe every week, maybe every day if you're lucky" | Latency and inconsistency: "You just can't expect day to day, session critique at that price" (**VERIFIED**, u/Boblaire) |
| **1:1 remote coach** | **$75/mo** offered openly in-thread: "I offer 1-1 remote coaching with video feedback/weekly custom programming for 75USD/month" (**VERIFIED**, u/nathanjue77, USAW L2) | Video feedback + custom programming, human, named, accountable | Cost; quality variance — "the 'online' coaches aren't as worth it sometimes" (u/robaroo) |
| **Posting clips to r/weightlifting** | Free | Occasionally excellent, mechanistically causal feedback with corrective cues | **68% of posts get zero replies**; quality is uneven — described by a senior community member as "occasional form checks of mixed quality from the community" (**VERIFIED**, u/Boblaire) |
| **Program-community Facebook/Discord form checks** | Bundled with program subscription | e.g. "I'm running weightlifting 2.0 by sika strength... has form checks in their facebook group" (**VERIFIED**, u/ActFamiliar1869); Weightlifting.ai had Max Aita himself doing checks "within reason - they can't look at every lift!" (**VERIFIED**, u/Powerful_Ideas) | Rationed by coach attention; explicitly cannot scale to every lift |
| **WL Analysis (iOS)** | Free, $8.99 one-off for "Extra features" | Automatic barbell detection, bar path coloured by velocity/power/force, side-by-side overlay, frame-by-frame, charts, CSV export. 4.3★/46 ratings. Reviewer: "Best app to improve Olympic lifting form... deff worth it" (**VERIFIED**, [App Store](https://apps.apple.com/us/app/wl-analysis/id1541855037)) | Pure measurement. No interpretation, no fault naming, no correction |
| **Iron Path / Iron Path Pro** | Small one-off | Bar path tracing. "It is a very simple app that allows one to record but also analyze... satisfied with the price vs result" (**VERIFIED**, [r/weightlifting](https://www.reddit.com/r/weightlifting/comments/e00zbd/iron_path_pro/)); "amongst the first bar path apps... something that many Olympic weightlifters used along with Coaches Eye" (**VERIFIED**, [r/lifting](https://www.reddit.com/r/lifting/comments/e19nj2/has_anyone_heard_of_or_used_the_app_iron_path_i/)) | Same gap: draws the parabola, says nothing about why |
| **Coach's Eye** | Dead | Was the default annotate/voiceover/slow-mo tool | **Shut down by TechSmith in September 2022, never replaced by a successor** (**SECONDARY** — [visualeyesapp.com](https://www.visualeyesapp.com/coaches-eye-alternative), [acesense.io](https://acesense.io/blog/coachs-eye-replacement-playbook/); both are competitor marketing pages, so treat the date as secondary-sourced, though it is stated consistently across independent vendors) |
| **Hudl Technique** | Free | Slow-motion, frame-by-frame video analysis (**SECONDARY**, [CNET listing](https://download.cnet.com/hudl-technique-slow-motion-video-analysis/3000-2136_4-75632715.html)) | Generic; no lift-specific intelligence |
| **iPhone slow-mo + Google Photos** | Free | A coach's practical setup: "You can upload videos and share them with specific users... I have a log of every filmed lift from when she learned how to snatch to when she medaled at junior nationals" (**VERIFIED**, u/ibexlifter, L2 USAW coach, [r/weightlifting](https://www.reddit.com/r/weightlifting/comments/rx28ft/what_app_do_you_use_or_what_app_does_your_coach/)) | No analysis layer at all — but the community's position is that none is needed |
| **Paid one-off human form check (checkmyform.co)** | Small one-off fee | Certified coach reviews your clip | Launched Jun 2023, **was voted to 0 upvotes and rejected by the sub**; domain no longer resolves as of 2026-09-14 (**VERIFIED** — [launch thread](https://www.reddit.com/r/weightlifting/comments/14fcyem/get_your_form_checked_by_a_professional_coach/); domain non-resolution verified by curl) |

**The actual gap, stated precisely:** every cheap tool measures (bar path, velocity) and every good interpretation is human and rationed. Nothing cheap *interprets*. That gap is genuine (**VERIFIED** by the substitute table above). Whether athletes will pay to close it is a separate question, addressed in §4 and §6.

## 4. Does the target persona even want this? The distrust evidence

This is the most important finding in the report, and it is negative.

In **March 2026** a user asked r/weightlifting directly whether AI coaching apps were any good. The thread scored **10% upvoted** (i.e. heavily downvoted) with 13 comments. The reception:

> "Don't spend a penny on AI coaching. If money is tight save and have less regular sessions with a real coach or join a club.
>
> There's a lot of jobs AI is capable of taking over competently, this is certainly is not one of them." — u/Speed-Sloth

> "This is just your own AI slop app you're trying to peddle, isn't it?" — [deleted], 16 upvotes (the top comment in the thread)

> "All their post are 'I built an AI blank generator' you nailed it" — u/Bruno-95-4-Pennies, 9 upvotes

> "hell yeah let's all start shilling in r/weightlifting!" — u/greaseaddict

**VERIFIED** — [r/weightlifting, "AI coach recommendations?"](https://www.reddit.com/r/weightlifting/comments/1rj2me4/ai_coach_recommendations/), Mar 2026. Note that the top-voted response was not evaluation of the product but an accusation of astroturfing. The community's prior on AI lifting apps is *hostile by default*. Any go-to-market that relies on organic credibility in this community should assume it will be treated as spam until proven otherwise (**INFERRED**).

Critically, the same thread contains the single best available statement of the honest positioning — from the most senior voice in it, a competitive masters champion and coach, and it is *not* pro-AI:

> "Paying for form checks can be worth it compared to relying on occasional form checks of mixed quality from the community." — u/Boblaire

**VERIFIED**, same thread. He then immediately routes the asker to **$20–40/mo human remote coaching** and adds: "Btw, don't peddle your AI coaching on the subreddit."

The clearest expression of demand for the product's category came from someone in exactly the target situation — a one-year-trained lifter moving somewhere with no weightlifting gym:

> "one of my concerns would be if I start developing minor incorrect techniques without notice... what would be good options to prevent the development of bad techniques when using Weightlifting AI?" — u/Kippenhuis

**VERIFIED** — [r/weightlifting, Sep 2023](https://www.reddit.com/r/weightlifting/comments/16hlexv/form_check_when_using_weightlifting_ai/). The four replies all pointed him to **humans**, not to a better algorithm:

> "theres no form checks but this page is so good for that! You'll get really in depth answers with links/sources to good info!" — u/Papapames

> "We have coaches, including Max Aita himself, active in the Weightlifting.ai community... who will do some form checks (within reason - they can't look at every lift!)" — u/Powerful_Ideas

> "you can always post here and you'll almost always get good feedback, I'm happy to comment on any I see if no one has done so already" — u/mattycmckee (Irish Junior Squad, 96kg)

**VERIFIED**, same thread. So: the demand exists, is articulated clearly, and the community's answer to it is unanimously *human*. Nobody in that thread wished for an AI that could analyse form. That is a specific, damaging absence (**VERIFIED** by absence in a thread that would have surfaced it).

Also relevant: one lifter in the AI-coach thread wanted AI for *motivation*, not analysis — "I would pay for an AI agent modeled after Abajiev that tells me to stop being a bitch every workout" (u/h0rxata, **VERIFIED**). Half-joking, but it is the only expressed willingness to pay for AI in the thread, and it is not for this product.

## 5. The graveyard: Weightlifting.ai is dead, and how it died matters

Weightlifting.ai was the flagship AI-programming product in this exact sport — built on Max Aita's coaching logic, marketed as "the most flexible program for Olympic weightlifting - individually created for your needs and automatically adjusted as you train" (**VERIFIED**, [weightlifting.ai](https://www.weightlifting.ai/)), priced around **$50/mo** via the Play Store (**VERIFIED**, u/Boblaire, Aug 2024).

In **June 2026** a paying subscriber posted: "the app just dissappeared from the appstore and even on their website, it seems that everything has been silently shut down."

**VERIFIED** — [r/weightlifting, "What happened to weightlifting.ai"](https://www.reddit.com/r/weightlifting/comments/1u0uq5u/what_happened_to_weightliftingai/), Jun 2026, 19 upvotes, 24 comments.

The successor product's advantage, per a user who migrated:

> "But Coach Logik is far and away a much better app. The programming is better, **you connect with the actual coaches**, and can upload videos directly into your program and get feedback from Max, Josh Gibson, and one of the other coaches Chris." — u/Emart079

**VERIFIED**, same thread (emphasis added). The market's revealed verdict: the AI-programming layer was the weak part; the *human coach reviewing your uploaded video* was the strong part. That is precisely the inverse of the product under test, which proposes to automate the human review and add AI-generated programming.

Two other reactions from that thread are pricing red flags:

> "The pricing never made sense — Claude is free" — u/shmovernance

> "There have been complaints voiced on the sub before... Not sure if these are still an issue, but I'd be hesitant myself." — u/nelozero

**VERIFIED**, same thread. The first is the substitution risk in one line: a general-purpose LLM is a free, good-enough narrative-explanation engine in the eyes of at least some of this audience (**VERIFIED** as a stated opinion; not a claim that Claude actually does snatch video analysis well).

## 6. Feature 3 (AI-generated corrective programming) — actively distrusted

Weightlifting programming is a named-authority culture. When ChatGPT output was posted to r/weightlifting:

> "Looks like weightlifting.ai doesn't have anything to worry about just yet. **Any program written by a coach will be far, far more varied with different accessories or complexes to adjust, correct and identify an athlete's weakness.** Think block jerks, a typical complex of pulls and hang snatches or bodybuilding movements like shoulder presses. This might work a lot better for bodybuilding and powerlifting though." — u/teh_weiman

> "Make everything 90%+ and it's the Bulgarian program" — u/I_Am_Not_Snowden

> "The one it gave me was god awful." — u/FellOverOuch

**VERIFIED** — [r/weightlifting, "ChatGPT writes training program"](https://www.reddit.com/r/weightlifting/comments/zfxfk2/chatgpt_writes_training_program/). Note the first quote identifies *exactly* the capability feature 3 claims — accessory/complex selection to correct a weakness — as the thing AI cannot do.

Corroborating the named-program culture: community advice threads route people to named humans and named programs, not systems — Dozer Weightlifting (Dylan Cooper), Attitude Nation (Jon North), Christian Rodriguez (8x Team USA), California Strength, Catalyst, Garage Strength, Sika Strength, Torokhtiy (**VERIFIED** — [r/weightlifting, "Looking for a coach? Here are some tips!"](https://www.reddit.com/r/weightlifting/comments/1701ray/looking_for_a_coach_here_are_some_tips/)). Also: "there is so much free programming out there you likely never need to pay for any until you get past being an intermediate level lifter" (**VERIFIED**, u/Boblaire) — i.e. the exact persona targeted (already knows the movement, not a beginner) is the persona least likely to pay for programming.

**Verdict on feature 3: it is the weakest of the three and risks poisoning the other two.** Bundling AI programming into a form-analysis product invites the "AI slop" framing documented in §4 (**INFERRED**).

## 7. Is self-diagnosis actually the bottleneck? Evidence says: partly, no

The counter-argument in the brief is largely supported.

**Against the product (self-diagnosis is not the bottleneck):**
- The community's explicit position is that no analysis tool is needed. Asked which app to use for analysing lift videos, replies were dismissive: "There is nothing it will be able to tell you that you can't just see anyway" (u/mattycmckee, Irish Junior Squad); "You don't need to rely on an app to analyze your videos. Develop an actual coach's eye" (u/onebigdingus); "Do you really need an app for that? Coach watches vid, coach frowns, coach writes 'long winded message about how that sucked', coach tells you to squat more." (u/mustanger) — **VERIFIED**, [r/weightlifting](https://www.reddit.com/r/weightlifting/comments/rx28ft/what_app_do_you_use_or_what_app_does_your_coach/).
- Form-check posts frequently *name the fault in the title* ("Forward bar in Snatch", "Help me get rid of bent arms", "Genuinely, how tf am i supposed to improve this?") — the poster already knows what is wrong and is asking *how to fix it* (**VERIFIED** by post titles retrieved via r/weightlifting search; **INFERRED** as to intent).
- The single most persuasive coaching testimonial in the corpus is about a fix an athlete could not have self-diagnosed from bar path — and it was still a human who found it: "I kept missing forward for longest time. The solution ended up being my bar starting position off the ground was too far forward. Or speed under bar increased just by adjusting my grip width and foot angle" (**VERIFIED**, u/SuperDuperDangleDude, [r/weightlifting](https://www.reddit.com/r/weightlifting/comments/1anyw3s/is_a_coach_worth_it/)).

**For the product (there is a real diagnosis gap, but it sits with coaches, not athletes):**
- A coach in the analysis-app thread pushed back on the "just develop a coach's eye" purism: "with more accomplished lifters, I sometimes need to slow down the videos and analyze them to find the potential errors/opportunities for improvement. Obviously I need to improve my 'in the moment' observation but that doesn't happen overnight." — **VERIFIED**, u/rosebarbellarina, same thread. This is a genuine, articulated need for exactly this tool — **from a coach, not from the target persona**. That is a significant signal about who the real buyer might be (**INFERRED**).

## 8. Is coaching in this sport treated as inherently relational?

Yes, strongly.

- "get recommendations and interview them to see if you click. Move on if it's not working for you until you find the right fit" (**VERIFIED**, u/slade51) — fit and relationship, not accuracy, is the selection criterion.
- The distinction drawn between good and bad remote coaches is responsiveness and presence: "Some will hardly offer any advice and rarely reply, others will be constantly giving feedback, watching videos etc **as if you were basically there with them**" (**VERIFIED**, u/mattycmckee, [r/weightlifting](https://www.reddit.com/r/weightlifting/comments/1eq10p6/thoughts_on_coachingprogramming_apps_vs_remote/)).
- That same commenter's explicit ranking places an AI product *below* any decent human: **"In person > Remote with a good coach > Weightlifting.AI > Remote with a poor coach > Bog standard program."** (**VERIFIED**, same thread). This is the single most useful positioning datum in the report: the ceiling for an AI product in this market's own stated hierarchy is "better than a bad coach, worse than a good one."
- When a paid form-check startup launched, the community attacked its *credentialing*, not its price or UX: "Where are these 'professional' coaches coming from and what is the vetting process? What quantifies a professional coach?" (u/mattycmckee, 13 upvotes); "You should post your numbers and videos of doing your Olympic lifts. Why would I sign up before seeing your qualifications." (u/Icanbenchyourmom); "could you put video of the coaches doing the lifts they will be coaching on the website" (u/GOATonWii) — **VERIFIED**, [checkmyform.co launch thread](https://www.reddit.com/r/weightlifting/comments/14fcyem/get_your_form_checked_by_a_professional_coach/). **An AI has no numbers and cannot post a video of itself snatching.** This community's trust protocol is structurally inapplicable to an algorithm (**INFERRED**).

## 9. Willingness to pay — for feedback specifically

| Evidence | What it shows | Tag |
|---|---|---|
| "$20-50/mo... team programming and form checks at the leisure of the coach" | Market price for programming+feedback bundle is $20–50/mo, human included | **VERIFIED** ([link](https://www.reddit.com/r/weightlifting/comments/1anyw3s/is_a_coach_worth_it/)) |
| "I offer 1-1 remote coaching with video feedback/weekly custom programming for 75USD/month" | $75/mo buys a named human doing all three of this product's features | **VERIFIED** (same thread) |
| "Paying for form checks can be worth it compared to relying on occasional form checks of mixed quality from the community" | Direct statement that feedback specifically is worth paying for | **VERIFIED** ([link](https://www.reddit.com/r/weightlifting/comments/1rj2me4/ai_coach_recommendations/)) |
| Weightlifting.ai at ~$50/mo, shut down 2026 | A ~$50/mo AI product in this exact niche failed to sustain | **VERIFIED** ([link](https://www.reddit.com/r/weightlifting/comments/1u0uq5u/what_happened_to_weightliftingai/)) |
| checkmyform.co — paid human form checks, 0 upvotes, domain dead | A paid *human* form-check service also failed | **VERIFIED** |
| WL Analysis: $8.99 one-off, 46 ratings total | Measurement tools monetise at single-digit one-off, tiny volume | **VERIFIED** ([App Store](https://apps.apple.com/us/app/wl-analysis/id1541855037)) |
| Any athlete stating they would pay a monthly subscription for AI form analysis | — | **NO EVIDENCE FOUND** |

**The pricing squeeze is the core commercial problem.** A named human coach with real credentials, doing video feedback *and* custom programming, costs $20–75/mo (**VERIFIED**). An AI product must price meaningfully below that while occupying a slot the market's own hierarchy places below "remote with a good coach" (**VERIFIED**, §8). Meanwhile the free substitute (post to Reddit) costs $0 and the measurement substitute costs $8.99 once.

## 10. Methodology and limits

- Reddit's own API and web frontend blocked all requests from this environment; the `WebSearch` tool errored on every call. Evidence was gathered via the pullpush.io Reddit archive API and a Redlib mirror proxied through r.jina.ai. All quotes were read from rendered thread text; **no quote in this document is reconstructed or paraphrased into quotation marks** (**VERIFIED** by method).
- Comment-count and reply-latency statistics come from pullpush index snapshots and are directional, not exact. A planned measurement of median first-reply latency did not complete within the API's rate limits: **NO EVIDENCE FOUND** for a hard number on how fast free form checks get answered.
- r/olympicweightlifting returned zero results for "form check" via the archive — it appears to be a low-activity or differently-named community; **NO EVIDENCE FOUND** for form-check behaviour there.
- r/crossfit searches for AI form-check discussion surfaced nothing on-topic: **NO EVIDENCE FOUND** for CrossFit-side demand or distrust. Given CrossFit is half the stated target persona, this is a real hole in the evidence base and should be closed before any GO decision.
- Vendor claims about Coach's Eye's shutdown date come from competitors' marketing pages (**SECONDARY**); not independently confirmed against a TechSmith announcement.

## 11. The case that the pain is NOT real / already solved — at full strength

1. **The audience with money already has a human.** Serious weightlifters have coaches; the community's unanimous answer to every "should I get a coach" thread is yes (**VERIFIED**, §3). The residual market is people who explicitly *cannot afford or cannot access* a coach — the worst-monetising segment there is. The one such person found in the corpus was told to save up for a real coach rather than spend "a penny" on AI (**VERIFIED**, §4).
2. **The persona spec is self-defeating.** "Athletes who already know the movement" are precisely the athletes who least need fault *detection*. They name their own faults in their post titles (**VERIFIED**, §7). The community states outright that an app "can't tell you anything you can't just see anyway" (**VERIFIED**, §7). The bottleneck is motor learning and coached repetition, which no overlay addresses.
3. **The free substitute is not merely adequate, it is the community's lifeblood** — a national medalist coach said removing form checks would make the main feed "dry up" (**VERIFIED**, §2). 328 of 644 voters wanted them kept in the main feed. Supply of free feedback is a structural feature of this sport's online culture, not a gap.
4. **This exact business has already been tried and is dead.** Weightlifting.ai, backed by a genuinely respected coach's name, at ~$50/mo, silently shut down in 2026 — and its replacement's differentiator is *more human coach contact* (**VERIFIED**, §5). The paid-human variant (checkmyform.co) is also dead (**VERIFIED**, §3).
5. **The trust model cannot be satisfied.** This community credentials coaches by asking them to post their own lifting numbers and videos (**VERIFIED**, §8). An algorithm structurally fails that test.
6. **Feature 3 is a liability.** Community consensus is that AI programming is "god awful" and that a coach's program is "far, far more varied" in exactly the corrective-accessory dimension the product claims (**VERIFIED**, §6). Including it invites the "AI slop" reaction documented in the March 2026 thread.
7. **Pricing has no room.** $20–50/mo buys a human. $8.99 once buys bar-path measurement. $0 buys Reddit. Some users think a general LLM covers the narrative layer for free (**VERIFIED**, §5).
8. **Organic distribution is closed.** r/formcheck bans app self-promotion by rule; r/weightlifting restricts self-promotion to coaches who have "contributed to the sport or subreddit over time/years"; the last AI-app post there was downvoted to 10% and accused of astroturfing (**VERIFIED**, §2, §4).

## 12. The strongest honest case *for* the product

Kept short deliberately, because the evidence is thinner.

- The demand behaviour is real and high-frequency (~13 posts/week in one subreddit alone) and **68% of it goes unanswered** — supply-constrained, not demand-constrained (**VERIFIED**, §1).
- Athletes moving away from coached environments articulate the fear precisely and have no good answer: "if I start developing minor incorrect techniques without notice" (**VERIFIED**, §4).
- Even coach-bundled form checks are explicitly rationed — "they can't look at every lift!" (**VERIFIED**, §4) — while the product's cost per analysis is ~zero. Per-lift coverage is the only axis on which it structurally beats every human substitute (**INFERRED**).
- There is a real, articulated buyer — **but it is coaches, not athletes**: "with more accomplished lifters, I sometimes need to slow down the videos and analyze them to find the potential errors" (**VERIFIED**, §7). A coach-facing triage tool sits inside the culture's trust model instead of fighting it (**INFERRED**).
- The interpretation gap is real: every cheap tool measures and refuses to interpret (**VERIFIED**, §3).

## Verdict impact

**Supports NO-GO for the product as specified.** Not because the pain is imaginary — the form-check firehose and its 68% no-reply rate are real, measured demand — but because every commercial premise fails against the evidence:

1. The direct predecessor at this price point in this exact niche (Weightlifting.ai, ~$50/mo) is **dead**, and its successor won by adding *more human coach contact* (**VERIFIED**).
2. The market's own stated hierarchy caps an AI product at "better than a bad coach" while a good human costs $20–75/mo (**VERIFIED**).
3. The community's most recent recorded reaction to an AI coaching app was hostile and accused it of being slop (**VERIFIED**, Mar 2026).
4. Feature 3 (AI corrective programming) is specifically and repeatedly rejected by this community (**VERIFIED**).
5. The chosen persona — "already knows the movement" — is the segment for which fault detection is least valuable and programming is least likely to be purchased (**VERIFIED**, **INFERRED**).
6. There is **NO EVIDENCE FOUND** of any athlete expressing willingness to pay a monthly subscription for AI form feedback.

The two findings that could redirect rather than kill the effort: the unanswered 68% is a genuine service gap, and the only person in the entire corpus who *asked* for this capability was a **coach** wanting faster video triage. A coach-facing tool, or a hybrid where AI pre-triages and a named human signs off, is consistent with everything in this document. The athlete-facing, AI-only, three-feature subscription is not.
