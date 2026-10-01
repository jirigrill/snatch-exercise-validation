# 09 — Pose / body-model licensing: which model can we SELL?
Status: draft · Licences checked: 2026-10-01 · Scope: commercial iPhone app, single side-on camera, 240 fps, plates occlude limbs, deep squat, overhead bar

## Headline
The licensing split is cleaner than the accuracy split. **Anything that needs SMPL/SMPL-X body-model files (HMR2.0, WHAM, GVHMR, TRAM, CameraHMR, SMPLer-X) is commercially blocked until a paid Meshcapade SMPL licence exists, and even then the status of the *trained weights* is a legal grey zone.** The SMPL licence says it "prohibits the use of the Software to train methods/algorithms/neural networks/etc. for commercial, pornographic, military, surveillance, or defamatory use of any kind" ([smplx LICENSE](https://github.com/vchoutas/smplx/blob/main/LICENSE)). Permissive MIT *code* licences do not cure this. The clean paths are: (a) **Apache-2.0 2D pose** (RTMPose/MMPose, ViTPose) + our own angle maths; (b) **Meta SAM 3D Body + MHR** (SAM License + Apache-2.0 body model, no SMPL); (c) **Apple Vision / MediaPipe** (platform/Apache). Sapiens, OpenPose, Theia3D are blocked; YOLO-pose needs a paid Ultralytics licence.

**Testing decision (developer, 2026-10-01):** for the repeatability prototype (#11) we run **all candidate models, including licence-blocked ones**, purely to compare performance. A licence-blocked model that performs well is a reason to look for a licensed route (paid licence, clean alternative), not a model we may ship. Results for blocked models must be labelled "research-only, not shippable" in the writeup.

Method note: licence text below was retrieved via a page-fetch tool that summarises pages; quoted strings come from those retrievals. Anything not retrieved from a primary source is marked **UNVERIFIED**. Not legal advice: have counsel read the SAM License, SMPL licence and dataset terms before launch.

## 1. Verdict table (licensing)

| Model | Code licence | Weights licence | Body-model dependency | Training-data restriction | Verdict |
| --- | --- | --- | --- | --- | --- |
| **HMR2.0 / 4DHumans** | MIT (UC Regents, S. Goel) [LICENSE.md](https://raw.githubusercontent.com/shubham-goel/4D-Humans/master/LICENSE.md) | **UNVERIFIED** (checkpoint auto-downloaded; no separate weights licence found) | SMPL neutral, must register at smpl.is.tue.mpg.de ([README](https://github.com/shubham-goel/4D-Humans)) | Trained on H36M, COCO, MPII, 3DPW, AI-Challenger, InstaVariety etc. **UNVERIFIED per dataset**; H36M academic-only (below) | **Needs paid licence + legal review** (SMPL; weights trained under non-commercial SMPL/H36M terms) |
| **WHAM** | MIT (S. Shin 2023) [LICENSE](https://raw.githubusercontent.com/yohanshin/WHAM/main/LICENSE) | **UNVERIFIED** | SMPL/SMPLify registration ([README](https://github.com/yohanshin/WHAM)) | AMASS (no commercial training), 3DPW, RICH, EMDB, H36M; also depends on ViTPose, DPVO/DROID-SLAM | **Needs paid licence + legal review** |
| **GVHMR** | Custom academic: "educational, research and non-profit purposes only"; derivatives "must be open-source and prohibited for commercial use"; commercial contact xwzhou@zju.edu.cn [LICENSE](https://raw.githubusercontent.com/zju3dv/GVHMR/main/LICENSE) | Same repo licence (**UNVERIFIED** separately) | SMPL/SMPL-X | AMASS, H36M, 3DPW, BEDLAM (UNVERIFIED list) | **Research-only** unless ZJU grants a commercial licence AND SMPL licensed |
| **TRAM** | MIT (Y. Wang 2024) [LICENSE](https://github.com/yufu-wang/tram/blob/main/LICENSE) | **UNVERIFIED** | SMPL + SMPLify registration; README: "Thirdparty models have their own licenses" ([README](https://github.com/yufu-wang/tram)) | BEDLAM/3DPW etc. (UNVERIFIED); needs DROID-SLAM/masked-SLAM | **Needs paid licence + legal review** |
| **CameraHMR** | Search snippet says "CC BY 4.0" for the work, "code and pseudo ground truth data are available for research purposes" (**UNVERIFIED**, repo page showed no licence text; [repo](https://github.com/pixelite1201/CameraHMR)) | **UNVERIFIED** | SMPL; commercial enquiries to ps-licensing@tue.mpg.de (UNVERIFIED source: search snippet) | Needs registration for pseudo-GT on COCO/MPII/AIC/INSTA; BEDLAM/BEDLAM2 | **Unclear -> treat as research-only** |
| **SMPLer-X / SMPL-X family** | Repo has a LICENSE, type **UNVERIFIED** ([repo](https://github.com/caizhongang/SMPLer-X)) | **UNVERIFIED** | SMPL-X: "any use for commercial... purposes is prohibited... incorporation in a commercial product, use in a commercial service"; commercial via Meshcapade / smpl@max-planck-innovation.de ([SMPL-X licence](https://smpl-x.is.tue.mpg.de/modellicense.html)) | 32 training datasets incl. H36M, 3DPW, MSCOCO, AGORA, BEDLAM; "each dataset has individual ... terms" | **Needs paid licence**; weights status unclear |
| **SAM 3D Body (Meta)** | "checkpoints and code are licensed under SAM License" [repo](https://github.com/facebookresearch/sam-3d-body); SAM License: "non-exclusive, worldwide, non-transferable and royalty-free limited license" to use, reproduce, distribute, modify; no commercial restriction; bans ITAR/military/weapons end-uses, no reverse engineering, terminates if you sue Meta for patent infringement [LICENSE](https://raw.githubusercontent.com/facebookresearch/sam-3d-body/main/LICENSE) | Same SAM License; HF checkpoints gated (must "agree to share your contact information") [HF](https://huggingface.co/facebook/sam-3d-body-dinov3) | **MHR (Momentum Human Rig): Apache-2.0** [MHR repo](https://github.com/facebookresearch/MHR). No SMPL needed | Training dataset released on HF under "their dataset terms"; training-data composition **UNVERIFIED** (README silent; could include non-commercial sets, Meta asserts weights licence regardless) | **Commercially usable as-is per licence text** (strongest candidate). Residual risk: SAM License is custom, not OSI; read in full. Check training-data provenance claims |
| **Sapiens (Meta)** | Custom LICENSE ("portions ... Apache 2.0") [repo](https://github.com/facebookresearch/sapiens) | **CC-BY-NC-4.0** [HF sapiens-pose-1b](https://huggingface.co/facebook/sapiens-pose-1b); repo LICENSE is also CC BY-NC 4.0 ([raw](https://raw.githubusercontent.com/facebookresearch/sapiens/main/LICENSE)) | none | 300M human images (Meta-internal) | **Research-only** (NonCommercial) |
| **ViTPose** | Apache-2.0 [LICENSE](https://raw.githubusercontent.com/ViTAE-Transformer/ViTPose/main/LICENSE) | **UNVERIFIED** (checkpoints on Google Drive/HF; no separate weights licence found) | none | COCO, MPII, AI Challenger, CrowdPose (dataset terms UNVERIFIED; COCO annotations believed CC-BY 4.0 but [COCO terms page](https://cocodataset.org/#termsofuse) was not readable) | **Probably usable, verify weights + datasets** |
| **RTMPose / RTMO / MMPose** | Apache-2.0 (Open-MMLab) [mmpose LICENSE](https://raw.githubusercontent.com/open-mmlab/mmpose/main/LICENSE); rtmlib Apache-2.0 [repo](https://github.com/Tau-J/rtmlib) | rtmlib README: "users should verify individual model licenses ... for specific weights". Weights **UNVERIFIED** as Apache | none | COCO, COCO-WholeBody, HumanArt, UBody, "Body7" mix (AIC, CrowdPose, MPII, etc.; per-dataset terms UNVERIFIED) | **Probably usable as-is; verify weights + datasets** |
| **MediaPipe Pose (BlazePose)** | Apache-2.0 (+ small Lucent permissive part) [LICENSE](https://raw.githubusercontent.com/google-ai-edge/mediapipe/master/LICENSE) | Model card terms **UNVERIFIED** (model-card PDF not machine-readable). Docs: content CC BY 4.0, code samples Apache-2.0 [docs](https://developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker) | Uses Google GHUM internally (no licence burden on us) | Google proprietary data, **UNVERIFIED** | **Commercially usable (de facto, widely shipped)**; confirm model-card terms |
| **Apple Vision 2D/3D body pose** | Proprietary Apple framework | n/a (OS-bundled) | none | n/a | **Commercially usable under Apple Developer Program terms** (**UNVERIFIED**: no primary licence page fetched; API doc [VNDetectHumanBodyPose3DRequest](https://developer.apple.com/documentation/vision/vndetecthumanbodypose3drequest)). iOS-only lock-in |
| **YOLO-pose (Ultralytics)** | AGPL-3.0 [LICENSE](https://raw.githubusercontent.com/ultralytics/ultralytics/main/LICENSE) | "All Ultralytics YOLO trained models fall under the AGPL-3.0 License by default" [licence page](https://www.ultralytics.com/license) | none | COCO-keypoints | **Needs paid Enterprise licence** (required for "Develop commercial products", "Embed YOLO in ... edge devices"; price by quote, not public) |
| **MotionBERT / 3D lifters** | Apache-2.0 [LICENSE](https://raw.githubusercontent.com/Walter0807/MotionBERT/main/LICENSE) | **UNVERIFIED** | none (H36M skeleton, no SMPL) | Human3.6M: "Licenses free of charge are limited to academic use only" [H36M EULA](http://vision.imar.ro/human3.6m/eula.php); also AMASS, 3DPW, InstaVariety | **Unclear -> weights trained on H36M likely academic-only; retrain on own data to be clean** |
| **OpenPose** | CMU academic licence | same | none | COCO, MPII etc. | **Research-only**: "Academic or Non-Profit Organization Noncommercial Research Use Only" [LICENSE](https://raw.githubusercontent.com/CMU-Perceptual-Computing-Lab/openpose/master/LICENSE); commercial licence from CMU (fee not retrieved, UNVERIFIED) |
| **Theia3D** | Proprietary, desktop multi-camera | n/a | n/a | n/a | **Blocked**: ToS "research, sports performance, and educational use only", no resale/commercial use of Services [terms](https://www.theiamarkerless.com/legal/terms-of-use). Multi-camera anyway |
| **Move.ai API** | SaaS API | n/a | n/a | n/a | **Paid API; commercial/embedding terms UNVERIFIED** (pricing page 404'd). Search results (not primary): s1 single-cam $0.012/s, s2 $0.024/s; sales contact for bulk. Outputs mocap, cloud-only; not a measurement-grade joint-angle source |

### Dependency licences that decide the SMPL-family verdict

| Item | Terms (quoted) | Source |
| --- | --- | --- |
| SMPL model | Licensed for "non-commercial scientific research, non-commercial education, or non-commercial artistic projects"; commercial use "prohibited" incl. incorporation into commercial products; commercial licensing "through Meshcapade.com", smpl@max-planck-innovation.de | [SMPL licence](https://smpl.is.tue.mpg.de/modellicense.html) |
| SMPL/SMPL-X NN-training clause | "prohibits the use of the Software to train methods/algorithms/neural networks/etc. for commercial ... use of any kind" | [smplx LICENSE](https://github.com/vchoutas/smplx/blob/main/LICENSE) |
| SMPL commercial licence (Meshcapade) | Commercial licence covers "all the adult model variants of SMPL (SMPL+H, SMPL-X, STAR)" ([Meshcapade wiki](https://github.com/Meshcapade/wiki/blob/main/wiki/SMPL.md)). Pricing: Micro (individuals/startups/micro) EUR 5,000/yr; SME EUR 25,000/yr; Enterprise EUR 50,000/yr; perpetual option; 30-day free trial. **UNVERIFIED**: from search-result summary of Meshcapade's licensing page; direct page returned 403 / DNS fail. Confirm with Meshcapade | search snippet; [meshcapade.com/smpl](https://meshcapade.com/smpl/) (no prices on fetched page) |
| Meshcapade ownership | Epic Games acquired Meshcapade, announced Feb 2026 ([MediaPost](https://www.mediapost.com/publications/article/412940/epic-games-acquires-firm-that-makes-3d-humans.html), [MPG](https://www.mpg.de/26082348/max-planck-spin-off-draws-epic-games-to-tubingen)). Licence terms/prices may have changed since; re-verify | secondary |
| Does a SMPL commercial licence cover third-party *pretrained weights* (HMR2.0 etc.)? | Not stated in any retrieved primary source. **OPEN** | - |
| AMASS | "any use for commercial purposes, is prohibited"; "also prohibits the use of the Dataset to train methods/algorithms/neural networks/etc. for commercial use of any kind"; commercial: ps-license@tue.mpg.de | [AMASS licence](https://amass.is.tue.mpg.de/license.html) |
| Human3.6M | "Licenses free of charge are limited to academic use only"; commercial licensing by contacting authors | [H36M EULA](http://vision.imar.ro/human3.6m/eula.php) |
| COCO | Terms page not readable in this environment: **UNVERIFIED** (commonly: annotations CC BY 4.0, images subject to Flickr terms) | [COCO](https://cocodataset.org/#termsofuse) |
| 3DPW, BEDLAM, RICH, EMDB, AGORA | **UNVERIFIED** (3DPW/RICH/EMDB/AGORA are research-licensed to my knowledge; BEDLAM non-commercial by default) | not fetched |
| MHR | Apache-2.0 | [MHR LICENSE](https://raw.githubusercontent.com/facebookresearch/MHR/main/LICENSE) |

## 2. Technical profile

| Model | Output | Temporal? | Strengths | Weaknesses (occlusion / deep squat / overhead bar / mono) | On-iPhone | Speed (rough) |
| --- | --- | --- | --- | --- | --- | --- |
| HMR2.0 / 4DHumans | SMPL mesh/params per frame (+ tracking in 4DHumans/PHALP) | Per-frame; tracking only | Strong per-frame mesh, robust to unusual poses | ViT-H (~650M+) too heavy; per-frame jitter; plate occlusion untested; weak-perspective camera hurts side-on angles | No practical (server GPU) | Seconds/frame on phone-class HW; server only |
| WHAM | SMPL world-grounded motion + foot contact | Yes (video, SMPL-seq) | Temporal smoothing, global trajectory, foot contact | Needs ViTPose + DPVO; static camera ok; squat bottom hips ambiguity; heavy | No (server GPU) | Offline |
| GVHMR | SMPL world-grounded, gravity-view | Yes | Strong gravity-aligned output, good for static-cam lifts | Same; licence blocks | No | Offline |
| TRAM | SMPL in world coords, metric scale | Yes | Handles dynamic cameras | SLAM stage irrelevant for tripod; heavy | No | Offline |
| CameraHMR | SMPL, perspective-aware, dense kp | Per-frame | Better perspective/FOV handling than HMR2 (useful for close tripod) | ViT-H heavy | No | Server |
| SMPLer-X | SMPL-X whole-body | Per-frame | Generalist, big-data scaling | Heavy, hands/face wasted | No | Server |
| SAM 3D Body | MHR mesh + skeleton: body, feet, hands; promptable with 2D keypoints/masks | **Per-frame (single-image)**; no video support documented | Claims "superior handling of occlusions, hard poses"; prompts (2D kp/mask) let us inject RTMPose/own keypoints to anchor occluded joints. 3DPW MPJPE 54.8 | 631M-840M params: server only; no latency numbers published; need our own temporal filter; skeleton-vs-surface decoupling is good for joint angles | No (server). Distillation needed | UNVERIFIED (not published); ViT-H class = ~100s ms/frame on datacentre GPU |
| Sapiens | 2D pose 308 kp, seg, depth, normals | Per-frame | Very accurate, 1K res; dense incl. feet | NC licence; 0.3B-2B params | No | Server |
| ViTPose | 2D COCO 17 kp (+whole-body variants) | Per-frame | Accurate; many sizes (B/L/H) | 2D only; occluded joints guessed from context; needs lifting for depth | Possible via CoreML for ViT-B; heavy | ViT-B ~tens ms on GPU |
| RTMPose / RTMO | 2D 17/26/133 kp; RTMO one-stage | Per-frame | Real-time: RTMPose-m 75.8 AP, 90+ FPS i7 CPU; RTMPose-s 72.2 AP, 70+ FPS Snapdragon 865 ([MMPose](https://github.com/open-mmlab/mmpose/tree/main/projects/rtmpose)); ONNX/ncnn/TensorRT; Halpe-26 includes heel/toe | 2D only; plates occlude wrists/elbows; no 3D; need detector | **Yes** via ONNX Runtime / CoreML conversion | ~30-100+ FPS mobile (s/m) |
| MediaPipe Pose | 33 landmarks, 2D + "world" 3D (GHUM) | Per-frame + tracking smoothing | Built for fitness, on-device, iOS SDK, Lite/Full/Heavy | Single person ROI tracker loses lock in deep squat/inverted shapes; plates; limited accuracy at 240 fps motion blur; known weaker than RTMPose on hard poses (**not benchmarked here**) | **Yes** (iOS SDK) | Real-time (no numbers in docs) |
| Apple Vision 3D | 17 joints, metres, root at hip; 1 person | Per-frame (can use depth/LiDAR) | Zero model shipping, hardware-accelerated, free | One "most prominent person"; occlusion handling undocumented; 17 joints (no heel/toe, no wrist angle); 3D from single image uses 1.8 m default height without depth | **Yes** (native) | Real-time (Apple does not publish) |
| YOLO-pose | 2D 17 kp, one-stage | Per-frame | Fast, easy CoreML export | AGPL/paid; COCO-17 only | Yes (CoreML) | Real-time |
| MotionBERT & lifters | 3D H36M-17 from 2D sequence | **Yes** (243-frame window) | Temporal smoothing of 2D->3D; light vs mesh models | H36M-trained: upright, indoor, no barbell/deep-squat; 2D errors propagate; depth ambiguity side-on is minor for sagittal angles | Possible (small transformer) but windowed | Fast on GPU |
| OpenPose | 2D 25 kp | Per-frame | Historic baseline | Licence, slow | No | n/a |
| Theia3D | Multi-cam markerless 3D joint kinematics | Yes | Validated in literature | Multi-camera, desktop, licence | No | n/a |
| Move.ai | Cloud mocap from 1+ cams | Yes | Packaged | Cloud, video upload, not angle-grade, licence terms unknown | No (cloud) | Per-second billing |

## 3. Other serious candidates found
- **MHR as standalone**: Apache-2.0 parametric body ([repo](https://github.com/facebookresearch/MHR)); the only high-quality mesh/skeleton model with a clean commercial licence found. Lets us build our own mesh-fitting without SMPL.
- **Own 2D -> sagittal angles**: for hip/knee/elbow/trunk in a side view, 2D keypoints + own geometry avoids both SMPL and depth ambiguity. Licence-cleanest and fastest.
- **Not checked**: BlazePose-GHUM 3D licences beyond MediaPipe; YOLO-NAS / other Apache pose nets; DWPose (Apache, via MMPose family, UNVERIFIED); fine-tuning our own 2D model on labelled snatch frames (needs data licences we control).

## 4. Ranking: commercial-viable AND likely to handle occluded snatch

| Rank | Model | Licence status | Occlusion / squat outlook | Why |
| --- | --- | --- | --- | --- |
| 1 | **SAM 3D Body (+MHR)** | Clean on paper (SAM License, MHR Apache) | Best claimed ("occlusions, hard poses") | Only mesh-level model without SMPL; promptable with keypoints; server-side only; no temporal |
| 2 | **RTMPose-x/l (Halpe-26 or whole-body) + own angle maths + temporal filter** | Apache-2.0 code; weights/dataset terms to verify | Good on hard poses, but 2D occluded joints are guessed | On-device, 240 fps feasible, clean path; heel/toe keypoints help trunk/shank angles |
| 3 | **ViTPose-L/H** (as accuracy ceiling / teacher) | Apache-2.0 code; weights UNVERIFIED | Generally better than RTMPose on hard poses | Use server-side or to pseudo-label/distil |
| 4 | **Apple Vision 3D/2D** | OS API, fine | Unknown, single prominent person | Free baseline, easy, but low joint count and opaque |
| 5 | **MediaPipe BlazePose (Heavy)** | Apache-2.0 | Likely weaker on deep squat/plates (UNMEASURED) | Cheap baseline |
| 6 | **MotionBERT lifter** on top of rank 2 | Apache code; H36M weights doubtful | Temporal smoothing helps, domain gap | Only if retrained on clean data |
| - | YOLO-pose | Paid Enterprise licence, price unknown | Similar to RTMPose | No advantage over Apache RTMPose |
| Blocked | HMR2/WHAM/TRAM/CameraHMR/SMPLer-X | SMPL (EUR 5k/yr Micro, UNVERIFIED) + weights grey zone | Possibly best temporal | Pay and get counsel first |
| Blocked | GVHMR, Sapiens, OpenPose, Theia3D | Research/NC only | n/a | Do not test for transfer |

## 5. Recommendation for the repeatability test

**Run these (licence transfers to product):**
1. **SAM 3D Body (DINOv3-H+), prompted with RTMPose keypoints**, per-frame, then own temporal filter. Tests ceiling for occluded accuracy with a clean licence.
2. **RTMPose-x (or RTMW) via rtmlib/ONNX + own sagittal-angle code + One-Euro/Savitzky-Golay filter.** Tests the shippable on-device path.
3. **ViTPose-H (or Apple Vision 2D/3D as the zero-cost baseline)** as cross-check. Pick Apple Vision if you want a native iOS baseline; ViTPose if you want an accuracy ceiling.

**Optional "ceiling only" run, knowing it will not transfer:** WHAM or GVHMR to see whether temporal SMPL models are meaningfully more repeatable. Only worth it if you are willing to buy SMPL (Meshcapade) AND get counsel to rule on pretrained weights; otherwise skip.

**Licence-blocked for a commercial product (testing would not transfer):** GVHMR (academic licence), Sapiens (CC-BY-NC-4.0), OpenPose (non-commercial), Theia3D (research/sports-performance ToS, multi-cam), YOLO-pose (AGPL unless paid), and, until a SMPL licence plus weights opinion exists, HMR2.0 / WHAM / TRAM / CameraHMR / SMPLer-X.

## 6. Open questions
1. Does a Meshcapade SMPL commercial licence cover use of **third-party pretrained weights** trained under SMPL/AMASS/H36M terms (HMR2, WHAM, TRAM)? Ask Meshcapade/Max Planck Innovation in writing. Post-Epic acquisition (Feb 2026), are tiers and prices still EUR 5k/25k/50k?
2. SAM License: read the full text for field-of-use limits and redistribution of weights inside an app bundle vs server hosting. What is the SAM 3D Body training-data provenance (any non-commercial sets)? Does gated HF access add terms?
3. Weights licences for ViTPose, RTMPose (Body7/Halpe), MediaPipe model card: not found as separate documents. Dataset terms (COCO, MPII, AIC, CrowdPose, Halpe, 3DPW, BEDLAM) unverified.
4. Apple Developer Program licence/Vision terms for health/fitness claims and data handling: not fetched.
5. Move.ai API commercial terms (embedding in a paid app, data retention): pricing page 404, terms not found.
6. Ultralytics Enterprise price: quote only.
7. Accuracy/repeatability under plate occlusion has **not** been benchmarked here; no model in this doc has published numbers on weightlifting. The test must produce them.
8. Is a SAM 3D Body distilled/exported on-device model allowed under the SAM License (derivatives permitted per summary; confirm)?
