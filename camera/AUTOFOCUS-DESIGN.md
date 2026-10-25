# Surface Pro 7 camera focus repair

The front endpoint already produces readable text. Only WeChat's local preview
mirrors it. Keep the system output unchanged; investigate an application preview
setting without a per-app wrapper or reversing frames sent to other applications.

The rear DW9719 actuator moved successfully during a bounded standard-V4L2 scan.
At the prepared target, position 256 gave a processed-frame sharpness score of
485, compared with 184 at position 0. This is scene-specific evidence, not a
universal fixed-focus calibration.

Repair the sensor/lens association through normal V4L2 notifier registration.
Preserve the working raw node minimum of 64 and processed endpoints 0/1.

Two autofocus locations were considered:

1. **libcamera Simple + SoftISP:** standard camera controls and lens lifecycle,
   available to native users of this pipeline. Requires rebuilding matched
   libcamera components. This is the proposed approach, consistent with the
   user's request to fix the camera stack.
2. **The existing video bridge:** less work, but makes focus depend on that
   producer and leaves direct libcamera capture without autofocus. Do not use
   it as the primary repair.

The proposed libcamera repair adds a bounded coarse/fine contrast search using
unpacked RAW10 green samples, with exposure-normalized metrics, lens settling,
flat-scene failure detection, and conservative continuous refocusing. Only the
rear OV8865 with a working lens advertises autofocus. Support standard AfMode,
AfTrigger and AfState; do not invent a dioptre calibration for LensPosition.
The current frontend and per-user tuning files remain in place.

Verify the state machine on synthetic focus curves, bounds, flat/noisy scenes,
cancel/restart, missing lens and frame delay. Build against libcamera 0.7.2,
test from its build directory, then package matched libraries/IPA/tools/plugin
with a rollback to cached Arch packages. Live tests must show convergence on
the prepared target and refocusing after the target distance changes.

Do not claim calibrated rear colour reproduction. Compare the existing exposure,
contrast and colour controls on a fixed target only after focus is working.
