# 07 — Platform recommendation: web-only vs iOS-only vs both
Ticket: [#7](https://github.com/jirigrill/snatch-exercise-validation/issues/7) · Status: resolved · Date: 2026-09-14

## Headline

Build **iOS native only**. The product's core requirement — capturing the snatch turnover at a frame rate high enough to resolve it — is not reliably reachable from mobile web, and there is no evidence that iOS Safari exposes the 120/240fps slow-motion capture formats that AVFoundation exposes natively. Web-only is not a viable v1 for a capture-first product; Android is a deliberate deferral, not an oversight, because the monetising subscription demographic skews to iOS in the US and Health & Fitness converts better there. Cross-platform (React Native / Expo with `react-native-vision-camera`) is a legitimate fallback if Android becomes necessary, but for a solo developer chasing net $1-3k/month it adds a second capture surface to debug for no near-term revenue.

## Decision table

| Requirement | Web | iOS native | Android native | Cross-platform (RN/Expo) |
|---|---|---|---|---|
| Capture at 120/240fps | No — capped at 60fps, capabilities omit 120/240 (**VERIFIED**, [WebKit bug 320399](https://bugs.webkit.org/show_bug.cgi?id=320399)) | Yes — AVFoundation high frame rate capture since iOS 7 (**VERIFIED**, [Apple AVFoundation guide](https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/AVFoundationPG/Articles/04_MediaCapture.html)) | Yes on capable devices via Camera2 constrained high-speed session; not exposed by CameraX (**VERIFIED** for the CameraX gap, [CameraX video capture](https://developer.android.com/media/camera/camerax/video-capture)) | Yes — fps is a negotiated constraint, resolves to highest available (**VERIFIED**, [VisionCamera formats](https://visioncamera.margelo.com/docs/guides/formats)) |
| Exact frame-rate constraint honoured | No — `min`/`max`/`exact` unsupported (**VERIFIED**, [WebKit bug 189328](https://bugs.webkit.org/show_bug.cgi?id=189328)) | Yes, per-format lock | Yes, per-format | Yes, negotiated with inspectable result |
| Prescribed camera angle / framing overlay | Possible in DOM overlay | Full control | Full control | Full control |
| Video recording | MediaRecorder from Safari iOS 14.5; MP4/H.264/AAC only (**VERIFIED**, [caniuse](https://caniuse.com/mediarecorder), [WebKit blog](https://webkit.org/blog/11353/mediarecorder-api/)) | `AVCaptureMovieFileOutput` / `AVAssetWriter` | MediaRecorder / CameraX | Native modules |
| On-device pose inference (zero cloud cost) | TF.js/MediaPipe Web — works but CPU-bound, no NPU path (**INFERRED**) | Vision body pose, on-device (**VERIFIED** for existence, [WWDC20 session 10653](https://developer.apple.com/videos/play/wwdc2020/10653/)) | MediaPipe Pose Landmarker, on-device (**VERIFIED**, [Google docs](https://developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker)) | Either, via native module |
| Background / resumable upload of large video | No Background Sync in Safari or iOS Safari, any version (**VERIFIED**, [caniuse](https://caniuse.com/background-sync)) | `URLSession` background transfer | `WorkManager` | Native module |
| Offline-first in a bad-wifi gym | Weak — no background sync, eviction risk | Strong | Strong | Strong |
| Push notification / re-engagement | Home Screen web apps only, since iOS 16.4, requires install + user gesture (**VERIFIED**, [WebKit blog](https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/)) | Native APNs | FCM | Native |
| Payment take rate | ~3% card processing + Stripe Billing 0.7% (**SECONDARY** — US page redirected to EU pricing; EEA standard 1.5% + €0.25, Billing 0.7%, [Stripe](https://stripe.com/pricing)) | 15% under Small Business Program to $1M proceeds (**VERIFIED**, [Apple](https://developer.apple.com/app-store/small-business-program/)); US storefront may link out commission-free (**VERIFIED**, [App Review Guidelines 3.1.1(a)](https://developer.apple.com/app-store/review/guidelines/)) | 15% equivalent | Same as underlying store |
| Subscription conversion | Worst of the three (**INFERRED**) | Best — App Store download-to-paid beats Play in every category (**VERIFIED**, [RevenueCat SoSA 2025](https://www.revenuecat.com/state-of-subscription-apps-2025/)) | Lower revenue per install, $0.14 vs $0.38 global median (**VERIFIED**, same) | Store-dependent |
| Discovery | SEO on a low-volume niche term (**NO EVIDENCE FOUND** for search volume of "snatch form analysis") | App Store search + category | App Store search | Both stores |
| Solo-dev maintenance load | 1 surface, but fighting the platform | 1 surface, capture works | 1 surface, fragmented capture | 1 codebase, 2 capture surfaces to verify |

## The high-frame-rate capture constraint

This is the decisive section. Everything else in this document is a preference; this is a hard gate.

### The timing arithmetic

The turnover — the transition from the third pull through to the catch, where the bar rotates around the athlete and the elbows lock out — takes roughly **0.2s** (**ASSUMPTION**, taken from the brief; the coaching literature range for the turnover phase should be confirmed in issue #5).

| Capture rate | Frame interval | Frames spanning a 0.2s turnover |
|---|---|---|
| 30fps | 33ms | ~6 |
| 60fps | 17ms | ~12 |
| 120fps | 8ms | ~24 |
| 240fps | 4ms | ~48 |

At 30fps, six frames must carry the entire turnover. The specific faults a coach looks for in this phase — early arm bend, bar looping away from the body, a slow or late elbow turnover — are sub-frame events at that rate. At 60fps, twelve frames is marginal: enough to say the turnover happened, probably not enough to reliably localise *where* it went wrong, and certainly not enough for a frame-accurate visual fault overlay that the user will scrub through. At 120fps and above the phase is genuinely resolvable. (**INFERRED** — this is a reasoned position on sampling adequacy, not a measured result; the honest test is to capture the same lift at 30/60/120/240 and check whether the fault labels a human coach assigns are recoverable at each rate. That experiment has not been run and should gate the build.)

There is a second, independent problem at low frame rates: **motion blur**. Frame rate and shutter speed are coupled in practice on phone cameras, and a bar moving at snatch turnover velocities smears across a 33ms exposure. Blur degrades pose-estimation keypoint confidence precisely on the joints that matter. (**INFERRED** — no source measured for this product's specific setup.)

### What mobile web actually gives you

- `MediaTrackConstraints.frameRate` is Baseline-widely-available and Safari nominally supports it (**VERIFIED**, [MDN](https://developer.mozilla.org/en-US/docs/Web/API/MediaTrackConstraints/frameRate)). Support for the *property* is not the question.
- **On iOS, WebKit clamps camera capture to 60fps and does not expose the 120/240fps formats at all.** An open WebKit bug ([320399](https://bugs.webkit.org/show_bug.cgi?id=320399), filed 2026-07-27, status NEW, InRadar) reports that on an iPad Pro (M5) / iPadOS 26.3, `getSettings()` never reports above 60, `getCapabilities()` reports a max of 60 with 120 and 240 **absent entirely**, and requesting `frameRate: {exact: 120}` throws `OverconstrainedError`. The reporter attached a native Swift/AVFoundation probe on the *same device* enumerating 54 formats including 1280x720 and 1920x1080 at 30/60/**240**fps, and successfully applied 120 and 240fps. (**VERIFIED** as a filed, reproduced bug report; **SECONDARY** as a general statement about all iOS devices — it is one reporter on one device family, but the mechanism described, `AVVideoCaptureSource::generatePresets`, is not device-specific.)
- Constraint semantics are additionally broken: `MediaTrackConstraints.frameRate` "doesn't support max, min, exact" in WebKit ([bug 189328](https://bugs.webkit.org/show_bug.cgi?id=189328), NEW since 2018). A related max-frameRate bug ([261461](https://bugs.webkit.org/show_bug.cgi?id=261461)) was fixed 2026-01-20 but the fix was macOS-only and commenters report it still failing. (**VERIFIED**)
- Safari's MediaRecorder is MP4/H.264/AAC only, with no bitrate control and an open request for frame-rate control (**VERIFIED**, [WebKit blog](https://webkit.org/blog/11353/mediarecorder-api/), [bug 274222](https://bugs.webkit.org/show_bug.cgi?id=274222)). Even if the camera delivered 120fps, the encode path is unconfigurable.

Conclusion: **the prescribed-angle, high-frame-rate in-app capture the product is defined around cannot be built on mobile web today.** Not "is harder" — the capture formats are not reachable. This is a single point of failure for the web-only option and it does not depend on any of the monetisation or distribution arguments below.

### What native gives you

Apple has documented high frame rate ("SloMo") capture since iOS 7, with `AVCaptureDeviceFormat` returning "the supported media types, frame rates, field of view, maximum zoom factor, whether video stabilization is supported, and more", and `AVCaptureMovieFileOutput` which "automatically supports high frame rate recording" including selecting the H.264 pitch level and bit rate (**VERIFIED**, [Apple AVFoundation Programming Guide](https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/AVFoundationPG/Articles/04_MediaCapture.html) — note this archive was last updated 2015; current symbol names are `AVCaptureDevice.Format.videoSupportedFrameRateRanges`, `activeVideoMinFrameDuration` / `activeVideoMaxFrameDuration`, and `AVFrameRateRange`, which I could **not** fetch directly because Apple's current documentation pages render client-side and returned empty bodies. Treat the modern symbol names as **SECONDARY**.)

`react-native-vision-camera` reaches the same capability from JS: fps is expressed as a negotiated constraint (`{ fps: 60 }`), higher-priority constraints win, an out-of-range request such as `{ fps: 99999 }` resolves to "the highest available FPS range" rather than failing, and the negotiated result is inspectable via `onSessionConfigSelected` or `VisionCamera.resolveConstraints()` (**VERIFIED**, [VisionCamera formats guide](https://visioncamera.margelo.com/docs/guides/formats)). Caveat: that page names only 30/60/120 in an example capability list and never explicitly names 240, and gives no iOS-vs-Android split for frame rate. So "RN can do 240fps on iOS" is **INFERRED**, not verified.

## Web's other gaps (secondary, but they compound)

- **No background upload.** Background Sync is unsupported in Safari and iOS Safari at every version through 26.6 (**VERIFIED**, [caniuse](https://caniuse.com/background-sync)). A 240fps 1080p clip is large; if the athlete backgrounds the tab or the gym wifi drops mid-upload, there is no platform mechanism to resume. Native has `URLSession` background transfer for exactly this. This matters directly for the gym-context constraint.
- **Large-file handling is fragile.** iOS Safari aggressively reclaims memory from background tabs, and there is no durable, guaranteed-persistent store for multi-hundred-megabyte blobs. (**INFERRED** — widely reported developer experience, no single authoritative source located.)
- **PWA install and push exist but are conditional.** Web Push on iOS requires the site be added to the Home Screen with a manifest `display` of `standalone` or `fullscreen`, and permission may only be requested from a direct user gesture (**VERIFIED**, [WebKit blog, iOS 16.4](https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/)). That is an extra manual install step in the funnel before you can ever re-engage a user.
- **Apple has shown willingness to break PWAs.** In iOS 17.4 beta 1 (change made 2024-01-28) Apple removed Home Screen web apps in the EU; after ~6 weeks of public pressure and an EU DMA investigation it reversed, announced 2024-03-01, which "simply returns us back to the status quo" (**VERIFIED**, [Open Web Advocacy](https://open-web-advocacy.org/blog/apple-backs-off-killing-web-apps/)). The capability was restored, but a solo developer betting the whole product on a platform capability the platform owner tried to delete once is taking a risk with no mitigation.

## Android: why not yet

- **High-speed capture is fragmented.** CameraX — the modern, recommended API — exposes only `Quality.UHD/FHD/HD/SD` with **no frame-rate tier at all**, states "the eventual video codec and container format are not currently configurable", and warns that supported combinations "depend on the camera hardware capabilities" (**VERIFIED**, [CameraX video capture](https://developer.android.com/media/camera/camerax/video-capture)). High-speed capture requires dropping to Camera2's `CameraConstrainedHighSpeedCaptureSession` with the `CONSTRAINED_HIGH_SPEED_VIDEO` capability and querying `getHighSpeedVideoFpsRanges()` per device (**SECONDARY** — I could not retrieve the reference page body, only navigation chrome; the API names should be re-verified before relying on them). Per-device capability querying with vendor-specific gaps is exactly the maintenance burden a solo developer cannot absorb.
- **On-device inference is fine.** MediaPipe Pose Landmarker is "optimized for on-device, real-time fitness applications", outputs 33 3D landmarks, ships Lite/Full/Heavy variants, and supports Android/iOS/Web/Python. Models are freely downloadable; docs are CC-BY-4.0 and samples Apache-2.0 (**VERIFIED**, [Google](https://developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker)). So Android is not blocked on the ML side — only on capture.
- **The money is on iOS.** RevenueCat's State of Subscription Apps 2025: in every region, **more than 67% of apps draw at least 80% of revenue from iOS**; revenue per install after 60 days has a global median of **$0.38 on iOS versus $0.14 on Google Play** ($0.66 vs $0.35 in North America); and day-35 download-to-paid conversion is "consistently higher on the App Store than Google Play across all categories", with **Health & Fitness among the three biggest gaps** (**VERIFIED**, [RevenueCat](https://www.revenuecat.com/state-of-subscription-apps-2025/)).
- **Health & Fitness is a good category to be in.** Same source: highest revenue per install of any category (60-day median $0.63, P90 $4.19), best one-month realised LTV per payer (median $16.44, upper quartile $31.12), median trial-to-paid 39.9% with top decile 68.3%. Downside: refund rate 4.71%, second-highest of any category (**VERIFIED**, same).
- **Handset share does not favour iOS in Europe.** Statcounter, August 2026: US mobile OS is iOS 60.68% / Android 39.29%; Europe is Android 62.73% / iOS 37.25% (**VERIFIED**, [Statcounter US](https://gs.statcounter.com/os-market-share/mobile/united-states-of-america), [Europe](https://gs.statcounter.com/os-market-share/mobile/europe)). So iOS-only forfeits roughly two-thirds of European handsets. The RevenueCat revenue-concentration figures are what justify accepting that; handset share and paying-subscriber share are not the same thing.
- **Is the CrossFit/weightlifting demographic specifically iOS-skewed? NO EVIDENCE FOUND.** I found no platform-split data for CrossFit, weightlifting, or barbell-sport app audiences. The iOS-skew argument here rests entirely on the general subscription-revenue and Health-&-Fitness-conversion figures above, not on anything sport-specific. Do not present this as a demographic finding.

## Unit economics: on-device inference is the lever

Apple's Vision framework provides human body pose detection — "we will be providing hand pose and we will be providing human body pose from Vision framework", with multi-person body pose and grouped landmarks (face, arms, torso, legs) via `VNDetectHumanBodyPoseRequest` (**VERIFIED**, [WWDC20 session 10653](https://developer.apple.com/videos/play/wwdc2020/10653/)). Notably, that session never uses the phrase "on-device" — the strong implication comes from its discussion of per-device inference latency on older hardware and the ability to process whole image libraries. **Apple's explicit "runs on-device" claim: NO EVIDENCE FOUND on the pages I could retrieve** — the Vision and Core ML documentation pages render client-side and returned empty bodies. On-device execution is the correct and near-certain reading, but tag it **SECONDARY** in the report, not verified-by-quote.

The economic point stands regardless: pose extraction is free at the margin on-device, so the only recurring per-analysis cost is the LLM call for the narrative coaching and programming (issue #8's territory). This is the single largest factor in whether the freemium tier (~2 analyses/week) is survivable. Web-only would push pose extraction either to a CPU-bound JS runtime or to a server you pay for — the latter converts a fixed cost into a variable one at exactly the wrong point in the funnel.

ARKit / LiDAR: **NO EVIDENCE FOUND** that either helps here. LiDAR is short-range and present only on Pro devices; an athlete filming from across a platform with a phone on a plate is outside its useful envelope (**INFERRED**). Do not build the product story around it.

## Monetisation friction

- App Store commission is **15%**, not 30%, for any developer with under $1M in prior-year proceeds — and "developers new to the App Store" qualify (**VERIFIED**, [Small Business Program](https://developer.apple.com/app-store/small-business-program/)). At a $1-3k/month net target this business will never approach the $1M threshold, so the 30% figure is simply not the relevant number.
- Post-Epic, the US position changed materially. Judge Gonzalez Rogers' April 2025 contempt ruling found Apple had "willfully" failed to comply with the 2021 anti-steering injunction, barred Apple from taking any fee on external-storefront purchases and from scare-screening the link-out; the Ninth Circuit refused Apple's emergency stay on **2025-06-04** (**VERIFIED**, [Wikipedia: Epic Games v. Apple](https://en.wikipedia.org/wiki/Epic_Games_v._Apple)). Apple's own App Review Guidelines now read: entitlements for external purchase links "are not required for developers to include buttons, external links, or other calls to action in their **United States storefront** apps", and the anti-steering prohibition applies "in all other storefronts, except for the United States storefront, where this prohibition does not apply" (**VERIFIED**, [Guidelines 3.1.1(a) and 3.1.3](https://developer.apple.com/app-store/review/guidelines/)).
- **Caveat, and it is a real one:** the Supreme Court denied Apple's stay in May 2026 but **granted certiorari for the 2026 term** on the contempt question (**VERIFIED**, same Wikipedia source). The commission-free US link-out is therefore live but legally unsettled. Design for it as an optimisation, not a dependency.
- Net effect: **the "Apple tax" is no longer a reason to prefer web.** A US-storefront iOS app can offer StoreKit IAP at 15% for convenience-preferring users and a Stripe link-out at ~3% + 0.7% Billing for the rest (**SECONDARY** on Stripe's exact US rate — stripe.com/pricing and /us/pricing both served EU pricing to my fetches: EEA standard 1.5% + €0.25, international 3.15% + €0.25, Billing 0.7%). That is strictly better than web-only, which pays the low rate but suffers the conversion penalty documented above with none of the App Store's trust or payment-sheet friction advantage.

## Distribution and discovery

- **App Store search** gives a niche, high-intent term a fighting chance: a small category with few competitors is winnable, and the store handles payment trust and update delivery.
- **Web SEO for "snatch form analysis"**: **NO EVIDENCE FOUND** — I could not obtain keyword volume data (WebSearch was unavailable for the duration of this research; only direct page fetches worked). Two things are nonetheless clear without volume data: the term is low-volume by construction, and the word "snatch" carries severe SEO collateral — generic-language and adult-content collisions make organic ranking and paid acquisition both harder. (**INFERRED**)
- Neither channel is strong. Realistically, acquisition for this product is community-led — CrossFit affiliate gyms, coaching Instagram/TikTok, r/weightlifting — and those channels drive to whichever install target you name. That makes discovery close to platform-neutral, which removes it as an argument for web. (**INFERRED**)

## Gym context: the deciding practical test

The stated scenario is a phone propped against a plate, noisy room, poor or absent wifi, athlete between working sets with maybe 90 seconds of attention. Against that:

- **Web loses on capture** (60fps ceiling — see above), which is disqualifying on its own.
- **Web loses on upload.** No Background Sync means a dropped connection mid-upload is a lost rep with no automatic retry (**VERIFIED**, [caniuse](https://caniuse.com/background-sync)).
- **Web loses on the interaction model.** A Safari tab that must first be added to the Home Screen to get notifications, that can be evicted from memory, and that cannot hold a large pending upload durably, is a worse artifact to hand a sweating athlete than an app icon.
- **Native's advantage compounds:** capture, on-device pose extraction, and local queueing all work with the radio off. The upload and the LLM call are the only network-dependent steps, and both can be deferred. An iOS app can plausibly give the athlete the fault overlay *before* any network round-trip, with the narrative coaching arriving later — which is a materially better product, not just a better implementation. (**INFERRED**)

## Solo-developer cost

Two platforms is not 2x the work — it is worse than 2x on the one subsystem that matters, because camera capture is the least portable part of a mobile codebase and the part where Android fragmentation is severe. Every device-specific high-speed-capture quirk is a support ticket a solo developer must reproduce without owning the device.

React Native / Expo with `react-native-vision-camera` is the honest middle path and should be the *actual implementation choice* even for an iOS-only v1, because it preserves the Android option at near-zero incremental cost while shipping one platform. Its fps constraint model degrades gracefully rather than erroring (**VERIFIED**, [VisionCamera](https://visioncamera.margelo.com/docs/guides/formats)), which is the right behaviour across a heterogeneous device fleet. The cost is a native-module dependency on the critical path and a JS bridge in the capture pipeline. Verdict: **RN/Expo + VisionCamera, shipped to iOS only.** Swift/AVFoundation directly is defensible if the developer already knows it; the frame-rate capability is equivalent and the risk profile is lower, at the cost of closing the Android door.

Web still has one legitimate job: a **marketing and account-management site** — landing page, pricing, Stripe checkout for the link-out, coach-facing dashboard. That is cheap, does not touch the camera, and captures the payment-rate advantage. It is not "web-only"; it is web-as-adjunct.

## Recommendation

**Ship iOS-native only, implemented in React Native/Expo with `react-native-vision-camera`, plus a thin marketing/billing website. Do not ship Android until the iOS app has paying subscribers. Do not attempt web capture at all.**

Reasoning, in priority order:

1. **Capture is a hard gate and web fails it.** iOS Safari clamps `getUserMedia` to 60fps and does not enumerate the 120/240fps formats that AVFoundation exposes on the same hardware ([WebKit bug 320399](https://bugs.webkit.org/show_bug.cgi?id=320399)). A 0.2s turnover gets ~12 frames at 60fps. Every other consideration is downstream of this. If this bug were fixed tomorrow the analysis would be worth revisiting — it will not be fixed on a timeline a solo developer can plan around, and it has an 8-year-old sibling ([189328](https://bugs.webkit.org/show_bug.cgi?id=189328)) still open.
2. **iOS is where subscription revenue is.** >67% of apps take ≥80% of revenue from iOS; 60-day revenue per install $0.38 vs $0.14; Health & Fitness shows one of the largest App-Store-vs-Play conversion gaps ([RevenueCat](https://www.revenuecat.com/state-of-subscription-apps-2025/)).
3. **The commission objection is obsolete at this scale.** 15% under the Small Business Program, and US-storefront link-out to Stripe is currently permitted commission-free — though under Supreme Court review for the 2026 term.
4. **On-device pose keeps the freemium tier affordable.** Vision body pose costs nothing per inference, leaving the LLM call as the only variable cost.
5. **Android is a deferral with a known unlock condition:** ship it when iOS MRR justifies absorbing Camera2 high-speed fragmentation, not before. The RN choice makes that a port, not a rewrite.

What would change this recommendation: if the 30-vs-60-vs-120fps experiment (see below) shows that **60fps is sufficient** to recover the fault labels a human coach assigns, web-only becomes arguable again and the whole calculus reopens. That experiment is cheap and has not been run.

## Verdict impact

**Neutral on GO/NO-GO — but it removes an option and it surfaces one unrun experiment that is genuinely gating.**

- It is **not a NO-GO signal**: the product is technically buildable, the capture capability exists natively and is well-documented, on-device inference makes the unit economics work, and Health & Fitness is the best-monetising subscription category in RevenueCat's data. Nothing here says the product cannot exist.
- It is **not a GO signal either**: platform choice does not create demand. The binding questions remain market size (#1), willingness to pay (#2), and whether the analysis is good enough to be worth paying for (#5).
- **What it does do is kill web-only**, which was the cheapest path and the one a solo developer would most want to take. Removing it raises the floor on effort and means committing to a native release cycle, App Store review, and device-specific QA. That is a real cost against a net $1-3k/month bar, though not a disqualifying one.
- **The one item to escalate:** the claim that 120fps+ is *necessary* is **INFERRED**, not measured. If 60fps turns out to be sufficient, the platform constraint largely evaporates. If even 240fps proves insufficient to distinguish the faults reliably, that is a **NO-GO for the product**, not a platform problem. Run the frame-rate ablation before writing capture code — it is the highest-information, lowest-cost experiment available and it sits upstream of both this decision and issue #5.

