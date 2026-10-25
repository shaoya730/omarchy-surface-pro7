# Surface Pro 7 SoftISP autofocus

This local patch targets official libcamera **v0.7.2**, commit
`191e202178f02430b5942397c70d215cdd2056fa`. It enables standard
`AfMode`, `AfTrigger` and `AfState` only for an OV8865 sensor with a working
V4L2 focus lens. Other cameras retain their existing controls. The front system
output is not mirrored or otherwise transformed.

Apply `libcamera-0.7.2-softisp-af.patch` to that exact source, copy
`contrast_af.h` to `src/ipa/simple/`, and copy `focus_stats.h` to
`include/libcamera/internal/software_isp/`. Build matched libraries, IPA modules,
proxy workers, tools and GStreamer plugin. The tested build uses release
optimization with assertions enabled, `/usr` prefix, `lib` libdir/libexecdir,
automatic x86 pipelines, `ipu3,simple,vimc` IPAs, GStreamer and V4L2 enabled.
It retains the installed cam, qcam and lc-compliance tools. Documentation and
Python bindings were not installed on the test Surface and are disabled here.

`PKGBUILD` packages an already verified build using `LIBCAMERA_AF_SOURCE` and
`LIBCAMERA_AF_BUILD`. Its source-commit check does not replace build validation.
Meson regenerates signatures after removing build RPATHs; package options prevent
later stripping from invalidating them. Arch's compatibility-library signature
is also retained. Install the four matched packages together only after testing
their extracted IPA signatures and preserving the original four packages for
rollback.

## Algorithm and checks

The software ISP computes exposure-normalized contrast from unclipped RAW10
green samples. A bounded coarse/fine lens search discards in-flight frames and
allows lens settling. Flat scenes, cancellation, invalid bounds and lens write
failure have explicit outcomes. Continuous mode starts by default and uses
contrast changes to trigger another search after a cooldown. A full first search
took about 17 seconds on the test Surface; this is slower than a hardware ISP.
No calibrated dioptre scale is invented for `LensPosition`.

Run `tests/contrast-af.cpp` and `tests/raw10-focus.cpp` with ASan/UBSan. They cover
delayed feedback, bounds, convergence, flat scenes and recovery, cancellation,
lens failure, clipping, Bayer channel separation and brightness normalization.

Independent live tests on 2026-10-25 delivered 900 frames through native
GStreamer and reported a Scanning-to-Focused transition through native cam
metadata. A fixed-target comparison alternating lens positions 0 and 272 twice
gave sharpness scores about 60 and 320 at similar luminance, approximately 5.3x
for that target. This does not establish a general resolution or quality gain.
The front camera also completed a 60-frame capture with the modified build.

After installation, continuous mode detected deliberate defocus from a standard
V4L2 move to position zero and recovered Focused in 15.6 seconds. Moving the
printed target alone left the measured contrast nearly unchanged and did not
trigger a search; that distance-specific tracking check is inconclusive.

The sensor-to-lens ancillary link must exist and the DW9719 entity must have a
device node. Old media-ctl text output omits ancillary links; inspect the v2
Media Controller topology. `../ipu4p-rgb-notifier.patch` provides an optional
firmware-port exclusion mask, default zero. Enabling bit 6 requires confirming
that the unbound INT347E IR sensor is blocking notifier completion and that the
actual firmware maps it to port 6. Preserve RGB ports 3 and 7 and raw video64+
numbering. Never register all subdevice nodes from an unsynchronized lens probe.

Rear colour currently uses the existing identity-matrix configuration, without
a calibrated OV8865 colour profile. Autofocus does not provide Windows-equivalent
colour, denoising or hardware ISP processing. Native application preview and
cold-start persistence require separate verification after deployment.
