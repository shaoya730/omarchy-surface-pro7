# Surface camera autofocus implementation plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan inline. Review the final change with a fresh reviewer.

**Goal:** Make rear focus work through the standard libcamera Simple pipeline, preserving the working native WeChat endpoints.

**Architecture:** Add bounded contrast autofocus to the matching libcamera 0.7.2 software ISP. Keep the V4L2 lens lifecycle and standard AfMode/AfTrigger/AfState controls; keep camera selection and shared hardware ownership unchanged.

**Tech Stack:** C++17, libcamera 0.7.2, V4L2 DW9719, Meson/Ninja, Arch packages.

**Spec:** [Approved design](../../../camera/AUTOFOCUS-DESIGN.md).

## Constraints and review focus

- Front system output is correct; do not globally mirror it.
- Preserve processed video0/1 and raw video64+ numbering.
- Only the rear OV8865 with a real focus lens and supported RAW10 statistics enables AF.
- Do not expose an invented LensPosition dioptre scale.
- Guard lens bounds, stale frames, flat/noisy/overexposed scenes, restart/cancel, missing lens and I/O failure.
- Keep the currently installed camera stack until the independent build passes unit and live tests.
- Preserve a rollback of all replaced packages/configuration; no commits or pushes requested.

## Tasks

- [x] Reproduce rear focus error with a no-image-storage standard V4L2 scan.
- [x] Validate the sensor-to-lens ancillary link with Media Controller v2 after a complete reprobe.
- [x] Build unmodified official libcamera 0.7.2 in an isolated source directory.
- [x] Implement and run the real contrast state-machine regression test (RED already observed).
- [x] Add bounded RAW10 focus statistics and standard IPA/pipeline lens-control plumbing.
- [x] Build and test the modified library and its actual GStreamer camera path without installing.
- [ ] Compare focus/quality on a static target and after a distance change; confirm front capture unaffected.
- [x] Request review and repair important findings.
- [ ] Package matched components, back up current packages, install through system authentication and verify native preview.
- [ ] Verify cold-start lens association before claiming reboot persistence; document remaining colour calibration limits.

## Execution ledger

- User approved the standard-stack design on 2026-10-25.
- Reprobe now gives an ov8865-to-dw9719 ancillary link (flags 0x20000003) and a usable lens devnode. Legacy media-ctl text omits ancillary links; do not infer absence from its pad-link count.
- The earlier one-driver reprobe unbound the consumer lens; the revised complete sensor/lens sequence restored it. Persistent boot ordering still needs evidence.
- Official source commit: 191e202178f02430b5942397c70d215cdd2056fa (v0.7.2). Reference AF branch is old v0.3.2 and must not replace the installed version.
- Baseline build passed with private Python code-generator dependencies; system Python was not changed.
- The production release build includes all 25 installed targets, matched IPA signatures, and the IPA verifier. Four 0.7.2-4.1 packages retain every file shipped by the installed four 0.7.2-4 packages. All three extracted IPA modules pass signature verification against the packaged libraries.
- State-machine and RAW10 tests pass ASan/UBSan, including delayed frames, flat-scene recovery, cancellation and lens failure. Review corrections apply controls at the matching frame and pass measured scene contrast to the state machine.
- Independent native GStreamer capture delivered 900 frames in 30.81 seconds and selected lens position 272. Native cam metadata subsequently reported Scanning for 460 frames and Focused for 440 frames; the last eight frames were Focused in Continuous mode.
- Exposure-stable alternating V4L2 position tests gave sharpness 60.396/318.524/60.088/322.547 at positions 0/272/0/272, with luminance 186.18/183.00/186.07/182.94. The roughly 5.3x metric improvement is specific to this static target, not a universal quality or resolution claim.
- System front preview text is readable; the user sees mirroring only in WeChat. No global flip is applied.
- An optional ISYS firmware-port mask preserves default behaviour and can exclude failed IR port 6 only after the protected async pending list and actual software-node mapping confirm it on this Surface.
- Installation completed using system authentication. Protected async records confirmed INT347E was pending before the port-6 exclusion and absent afterward. The lens node was present after ISYS reload, raw nodes still start at 64, and processed video0/1 remain present.
- All four system packages are now 0.7.2-4.1. Installed native front capture passed 60 frames; installed native rear capture passed 900 frames with the final eight metadata states Focused. Original package identities, compressed archive integrity and backup hashes were verified before modification.
- Backup: `/var/lib/omarchy-surface-pro7/backups/autofocus7-20261025-152211`. Omarchy's Limine UKI was rebuilt; embedded kernel, release and command-line hashes match the previous UKI. Front/rear bridge services and WirePlumber were restored active. Cold-start and final native WeChat preview remain unverified.
- Installed continuous capture first focused at 17.0 seconds. After the user moved the target, measured contrast remained about 0.0167 versus 0.0169 at initial focus, so no rescan occurred. This distance-change test is inconclusive. A deliberate standard-V4L2 move to lens position zero then caused Scanning at 272.7 seconds and Focused at 288.3 seconds (15.6-second recovery), returning to position 224. This validates controlled-defocus recovery, not a distance-specific tracking claim.
- The user rebooted before the native WeChat check. The driver mask, video0/1, sensor enumeration and rear lens node survived; both producers instead failed before login ACLs arrived (`Permission denied`, lingering enabled, no restart policy). Added five-second on-failure retries and removed device-existence conditions that would otherwise skip retry. Both services recovered with the existing session ACLs. Four alternating 180-frame endpoint captures each delivered 90 distinct hashes in their final 90 frames; one short rear run had insufficient visible detail during exposure warmup and failed the older aggregate validator, so it is not counted as a full quality pass. A longer rear capture and restart-policy integration check follow.
- The longer post-boot processed rear endpoint test delivered 900 frames in 34.6 seconds, settled at lens position 272, and ended with a central sharpness metric of 116.938 and luminance around 194. An actual SIGKILL of each producer was followed by systemd recovery in 5.20/5.19 seconds, with new MainPIDs and incremented NRestarts. Both endpoints subsequently advertised Video Capture, YUYV 1280x720 at 30 fps. Full login-start verification after this service correction and native WeChat user confirmation remain pending.
- Native WeChat user validation failed with an application abort. The local core identifies CaptureThread and `video_capture_v4l2.cc:416`, `!race_checker416.RaceDetected()`. Disassembly corroborates the old checker lifetime around thread creation. Official WebRTC commit c420a240e19e02026f7dfec1261acc4153f1a1ff fixes that ordering. The current vendor DEB control metadata still reports 4.1.13.26, matching the installed package. No WeChat binary modification has been made; the user's scope decision on attempting a reversible application patch is pending. Details: `camera/WECHAT-CRASH-2026-10-25.md`.
- The user chose to retain official WeChat and collect crash evidence. The final integrity check reports 197 package files and zero altered files. A Chinese report, abbreviated fault stack and primary-source references are saved under `reports/wechat-camera-20261025/`, with a shareable ZIP in the outer workspace. The reported front mirror remains confined to WeChat's local preview based on the user's prior text-reference comparison; outgoing video direction is unverified. No binary patch, global image flip or external issue submission was performed. The application crash and preview mirroring remain unresolved by this evidence-only outcome.
