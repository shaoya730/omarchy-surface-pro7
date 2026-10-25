# Upstream baseline

- Repository: [omacom/omarchy-pkgs](https://github.com/omacom/omarchy-pkgs)
- Revision: [`eff382672f3a20a67a780cc2d3015b427e6b10ce`](https://github.com/omacom/omarchy-pkgs/tree/eff382672f3a20a67a780cc2d3015b427e6b10ce/pkgbuilds/linux-omarchy)
- Recipe: `pkgbuilds/linux-omarchy/PKGBUILD`, version `7.2.8-9`
- Local package: `linux-omarchy-bore-surface` and `linux-omarchy-bore-surface-headers`, version `7.2.8-4`
- Expected kernel release: `7.2.8-4-omarchy-bore-surface`

Upstream's `linux-omarchy` now contains the BORE kernel itself. The old `linux-omarchy-bore` is a transitional package and is no longer the source of the kernel recipe.

## Surface changes

All Omarchy upstream patches, detached signatures, and bundled PGP public keys are retained byte for byte. The upstream package pipeline metadata is not used by this standalone repository. The local recipe changes the package identity and revision, appends `0900-surface-pro7.patch`, `0901-ov8865-stream-lifecycle.patch`, and `0902-soundwire-link-count.patch`, and updates the patch and configuration checksums.

The x86_64 configuration adds these three modules to the Omarchy baseline:

```text
CONFIG_HID_SURFACE=m
CONFIG_HID_IPTS=m
CONFIG_LEDS_TPS68470=m
```

It also changes `CONFIG_PINCTRL_ICELAKE=m` to `CONFIG_PINCTRL_ICELAKE=y`, following linux-surface's Arch configuration so the driver is available before module loading.

`0900-surface-pro7.patch` adds IPTS, Ice Lake MEI/IOMMU support, Type Cover/HID fixes, camera sensor integration, the IPU IOMMU quirk, and TPS68470 LEDs. Revision 3 updates its synthesized IPTS report length as described below. The standalone IPU4P camera modules remain separate and must be rebuilt for this kernel before testing them.

The update from the 7.2.8-7 baseline also includes upstream's revised MacBook audio and Samsung 990 SSD quirks, the HP OmniBook TAS2783 stereo fix, and the printk startup change. It removes upstream's three Xe shrinker/hibernation patches that were dropped in 7.2.8-8.

## linux-surface synchronization on 2026-10-24

The Pro 7 changes were compared against [linux-surface/linux-surface revision 2294802a3f6eb8fc3cec502b5129b005c7c378db](https://github.com/linux-surface/linux-surface/tree/2294802a3f6eb8fc3cec502b5129b005c7c378db). The Omarchy Linux 7.2.8-9 baseline is retained.

- Backport [hid: ipts: Fix size of synthesized HID data report](https://github.com/linux-surface/kernel/commit/8399f8e20fd9de6d6ea222ac0313bf84a1419874): set `IPTS_HID_REPORT_DATA_SIZE` to 7488. The fallback descriptor declares 7485 payload bytes, two scan-time bytes, and a one-byte report ID; the previous value omitted the latter three bytes. Short reports can be dropped by the HID core on the fallback-descriptor path.
- Adopt `CONFIG_PINCTRL_ICELAKE=y` from the pinned official [Arch configuration](https://github.com/linux-surface/linux-surface/blob/2294802a3f6eb8fc3cec502b5129b005c7c378db/pkg/arch/kernel/arch.config).
- Backport the two OV8865 fixes from the same official camera patch set as `0901-ov8865-stream-lifecycle.patch`: [release the runtime PM reference on stream failure](https://github.com/linux-surface/kernel/commit/6b817645ff1a79bc5675ded96c9071a809cef6b6) and [program the negotiated mode on every stream start](https://github.com/linux-surface/kernel/commit/f709c5b71e5b80e737713cb6e989080076c04c42). The [Pro 7 camera driver project](https://github.com/georgemihaila/sp7-ipu4-camera/tree/aa0043f3649c3bff9247d5f99de5d164c3cdcc75) uses the kernel's OV8865 driver for the rear camera. The mode fix was originally validated upstream on an IPU3 Surface Book 2; its effect on this Pro 7 IPU4P setup still requires hardware testing.
- Retain the local Intel IPU `8086:8a19` passthrough quirk, the BORE and ADIOS patches, and the independent package names. Additional Surface drivers and the upstream 7.2.12 kernel base are outside this Pro 7 backport.
- Increment the local package revision from 2 to 3 and regenerate both BLAKE2b and SHA-256 checksums for the Surface patch and configuration.

`tests/test_ipts_descriptor.py` decodes the actual fallback HID descriptor and compares its input report length to the size sent by the driver. It reproduced the 7485-versus-7488 mismatch before the fix and passes with the backport. This is a descriptor-contract regression check, not a hardware touch test.

`tests/test_ov8865_stream.py` compiles the actual prepared kernel's stream callback into a device-call stub harness. Five cases failed before the backport; all six cases pass after it, covering already-powered mode programming, setup/control failures, and stream start/stop failures with balanced power references. This exercises callback control flow, not real sensor I/O.

## Revision 4: SoundWire ACPI bounds

`0902-soundwire-link-count.patch` is a local fix. The legacy master-count path computed `GENMASK(count - 1, 0)` before rejecting zero or excessive counts. This underflows for the Pro 7 firmware's zero-link value and triggers UBSAN. The patch constructs the fallback mask after the existing zero/maximum checks, preserving valid manager lists and link-selection quirks. UBSAN remains enabled.

`tests/test_soundwire_acpi.py` extracts the actual ACPI scan/link-selection functions and `GENMASK_TYPE` from the prepared kernel. With UBSAN enabled, the original code fails for zero, 65, and `UINT_MAX`; the patched code passes all nine SoundWire cases. All 16 Python regression cases pass on the revision 4 tree. Hardware validation is recorded separately below when completed.

### Revision 4 hardware checks on 2026-10-24

- The full Arch build and both package-content checks pass with Rust/BTF retained. Kernel SHA-256: `d44744ef9879413b2278b2276f881b2a1eb5c14b7758370f9ad90da921a27cea`; headers: `244a08d123837ac337b5160cea21ef93db3f246c591d4da48f0be175d0dad80c`.
- The Surface boots `7.2.8-4-omarchy-bore-surface`, boot ID `3cfc737a-f722-4608-a504-b6784cf0d148`. The old `linux`, `linux-omarchy`, `linux-surface` packages and their installed headers are removed at the user's request. Only the custom release remains under `/usr/lib/modules`; historical Snapper snapshots and installation backups are retained.
- No UBSAN, kernel BUG/Oops, or stream-start failure is found in this boot's verification journal. The zero-SoundWire-link probe messages remain; the working audio path uses HDA. The Surface speaker sink, IPTS, thermald, WirePlumber and camera bridge are active after testing.
- RTC-timed s2idle returns after 47 seconds to the same boot. Disk hibernation also returns to the original boot and desktop. The saved power trace contains `machine_suspend[4]` followed directly by `dpm_resume[64]` (`PMSG_RESTORE`), distinguishing actual image restoration from the snapshot THAW/rollback path. PM testing is disabled and the disk mode is platform. A post-resume clock correction means the recorded 11-second wall-clock delta cannot measure the actual powered-off interval; NTP subsequently synchronizes the clock. Automatic S4 RTC wake is not independently confirmed.
- The pinned IPU4P and modified OV5693 modules compile and install against the exact revision 4 headers. Firmware authentication succeeds. Both sensors deliver three raw frames with the expected total sizes (front 30,233,088 bytes, rear 47,941,632 bytes).
- After hibernation, the ordinary desktop user captures 30 processed frames from each camera. All 30 front frames have valid dimensions and visible tonal variation. Rear frames are valid but nearly uniform, with low contrast; rear image quality is not validated pending an unobstructed, illuminated-scene test. The rear lens device also lacks a V4L2 subdevice, so libcamera disables lens control. These are basic capture tests, not browser-meeting or autofocus validation.

## Checks performed for 7.2.8-3 on 2026-10-24

- Source SHA-256, all source/config BLAKE2b and SHA-256 checksums, array lengths, and all 172 existing detached patch signatures pass verification.
- All 175 patch files apply to the full Linux 7.2.8 source tree in recipe order with `--fuzz=0`; the final file contains both OV8865 commits.
- `make olddefconfig` retains the required Surface modules, `CONFIG_PINCTRL_ICELAKE=y`, `CONFIG_SCHED_BORE=y`, and the ADIOS module. The `8086:8a19` quirk is retained and the kernel release is `7.2.8-3-omarchy-bore-surface`.
- All seven Python regression cases pass with `KERNEL_SOURCE` pointing to the prepared tree, and the initramfs/Bash syntax checks pass.
- The Surface patch driver targets, Ice Lake pinctrl object, and OV8865 object compile successfully with GCC 15.2 in the isolated Ubuntu 26.04 WSL environment. As in the previous validation, missing local Rust/pahole tools disable Rust/BTF-related options in the validation tree only; the distributed configuration retains those Arch options.

- A complete Arch `makepkg` build succeeds with GCC 16.2.1 and the distributed Rust/BTF configuration retained. Both kernel and headers packages pass content, release, configuration, IPTS vermagic/BTF, and Rust metadata checks.
- The packages are installed on the Surface Pro 7, and a normal Limine reboot reaches `7.2.8-3-omarchy-bore-surface`. The new entry is first; the existing Arch and linux-surface fallback entries and UKI contents are preserved. The installed stock Omarchy package had no original boot entry on this machine.
- IPTS connects to `045E:099F`, `iptsd@dev-hidraw1.service` runs in touchscreen mode, the required Surface input modules are loaded, and thermald remains active with the machine's existing configuration. The user confirms touch, Type Cover keyboard, and audio work after reboot. No failed system units are reported.
- BORE is enabled (`kernel.sched_bore=1`). The ADIOS module is available; the NVMe drive still uses the existing `kyber` scheduler.
- Boot logs include a SoundWire ACPI zero-link probe warning and a UBSAN shift diagnostic in that probe. The active audio driver is `snd_hda_intel`, and PipeWire exposes the Surface speakers/headphones; audio works in the user's test. The sensor-hub and Bluetooth warnings also appeared before the upgrade. These warnings have not been patched by this revision.

Suspend/resume and real camera capture remain untested for revision 3. The separate IPU4P modules must still be rebuilt for the new kernel before testing that camera stack.

## Previous checks: 7.2.8-2 on 2026-10-21

- The downloaded Linux 7.2.8 source archive matches the pinned recipe's SHA-256.
- All 348 upstream patch, signature, and public key files match their pinned Git blobs; all 172 detached patch signatures verify against the bundled upstream signing key.
- All local source and configuration BLAKE2b/SHA-256 checksums pass, and the source/checksum array lengths match.
- All 174 patches apply in recipe order to the complete Linux source tree with `patch -Np1 --fuzz=0`.
- `make olddefconfig` resolves the configuration and retains the required Surface modules. `make kernelrelease` returns `7.2.8-2-omarchy-bore-surface`.
- The IPTS directory and every existing C file changed by the Surface patch compile successfully as kernel object targets with GCC 15.2 in Ubuntu 26.04 under WSL. This includes Surface HID, Type Cover, Intel IOMMU/MEI, camera integration, and TPS68470 LED support.
- The initramfs regression checks and Bash syntax checks pass.

The object compilation used the local host's resolved configuration: Rust and BTF-related options were disabled by `olddefconfig` because that environment lacks Rust and pahole. The distributed configuration retained the upstream Arch options plus the three Surface modules above. These checks do not constitute a complete Arch package build or linked bootable kernel. Hardware boot and runtime checks were not performed for that revision.

## Validation on Arch Linux

```bash
bash tests/surface-initramfs.sh
python3 -B -m unittest discover -s tests -p 'test_*.py' -v
cd kernel-bore
makepkg --verifysource
makepkg -s
```

After preparing a kernel source tree, run the rear-camera callback regression cases with a C compiler available:

```bash
KERNEL_SOURCE="$PWD/src/linux-7.2.8" python3 -B -m unittest discover -s ../tests -p 'test_*.py' -v
```

Install both the kernel and headers packages using the commands in the repository README. Keep a working kernel installed until the adapted kernel has passed the hardware checks there. Successful patch application or driver compilation alone does not validate boot, suspend/resume, or camera operation on a Surface Pro 7.
