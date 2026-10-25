# Experimental Surface Pro 7 IPU4P build

Current native WeChat status: camera capture can abort in its bundled WebRTC
thread startup check, and its front local preview remains mirrored. Both issues
are unresolved; the user chose to retain the official WeChat program. See the
[crash investigation](WECHAT-CRASH-2026-10-25.md) and
[Chinese evidence report](../reports/wechat-camera-20261025/报告.md).
System capture and autofocus tests below do not qualify native WeChat calls.

## Standard-stack autofocus repair

The [libcamera 0.7.2 autofocus patch](libcamera/README.md) adds bounded contrast
autofocus to the Simple software ISP using the rear OV8865's standard DW9719
lens control. On 2026-10-25, four matched 0.7.2-4.1 packages were installed after
independent build, signature and capture tests. The installed stack completed a
60-frame front capture and a 900-frame rear capture ending in Focused metadata.
A fixed-target test gave about 5.3x the sharpness metric at the automatically
selected position compared with position zero, at similar brightness.

The protected async wait list confirmed that failed INT347E IR discovery blocked
notifier completion. The optional `disabled_csi2_ports=64` setting excludes only
its verified firmware port 6, allowing normal completion to publish the late lens
node. This setting belongs to this tested Surface configuration; default zero
preserves the original discovery behaviour. RGB ports 3 and 7, processed video0/1
and raw video64+ remain available. The Omarchy UKI was regenerated and its kernel,
release and command-line hashes matched the previous image. The backup is
`/var/lib/omarchy-surface-pro7/backups/autofocus7-20261025-152211`.

Front system output already has readable text; only WeChat's local preview was
reported mirrored, so no global flip is applied. Rear colour calibration,
post-install native WeChat preview and cold-start persistence remain separate
validation items. The older notes below describe earlier stages.

### Startup permissions

The first reboot after the autofocus installation preserved the driver mask,
video0/1 and the rear lens devnode. Both user producers nevertheless exited
with `open v4l2loopback: Permission denied`: user lingering started them before
the active desktop session granted its device ACLs. The ACLs were present after
login, but the original services had no restart policy.

Both service templates now use `Restart=on-failure` and `RestartSec=5s`. The
front override clears the inherited device-existence condition; the rear unit
also allows an ordinary failed start when its device is not ready. This lets
systemd retry both missing-device and delayed-permission failures. No permanent
video-group membership or broader device permissions are required. Existing
installations need the updated units and `systemctl --user daemon-reload`, then
a service restart. A second reboot is still needed to validate the full login
sequence after this correction.

Post-boot endpoint tests delivered live front/rear frames. A longer 900-frame
processed rear capture settled at focus position 272 with stable brightness.
Simulating each producer's unexpected exit verified automatic recovery in about
5.2 seconds, with both endpoints again advertising YUYV 1280x720 capture at
30 fps. These checks validate service recovery; they do not replace the second
login-start test or final native WeChat confirmation.

## Native application device numbering

Native WeChat 4.1.13.26 scanned only `/dev/video0` through `63` on the test Surface. It listed the IPU4P raw/internal nodes and never opened the processed endpoints at `90` and `91`. No per-application launcher or device namespace is used for the system numbering repair.

`ipu4p-video-numbering.patch` adds the optional, read-only ISYS module parameter `video_nr_base` (default `-1`, preserving automatic allocation). With `video_nr_base=64`, raw nodes use high numbers; allocation that wraps below the configured minimum is rejected. `build.sh` applies this patch to the pinned camera checkout. The accompanying modprobe configuration reserves `video0` and `video1` for the front/rear processed endpoints, and the service templates use these numbers. These files must be installed together while camera consumers are stopped. Existing modules and configuration must be backed up before reloading. If the active initramfs embeds the old settings, regenerate it through Omarchy's Limine workflow as well.

The processed endpoints still use libcamera SoftISP and the shared hardware lock. This changes device presentation for native applications; it does not add hardware ISP support, fix rear autofocus, or allow simultaneous front/rear capture. Native WeChat preview and switching must be checked after deployment.

On the test Surface, the new ISYS module and global numbering were installed on 2026-10-25. The 55 raw nodes registered at `video64` through `video118`; a V4L2 scan of `video0` through `63` found exactly `Surface-Pro-7-Front` and `Surface-Pro-7-Rear`, both YUYV. The Omarchy UKI was regenerated because it embedded the previous modprobe settings; its kernel image, release and command line matched the original. The root backup is `/var/lib/omarchy-surface-pro7/backups/native-camera6-20261025-084909`.

After deployment, both endpoints passed two alternating 180-frame 1280x720 captures. All four runs had 90 distinct hashes in their last 90 grayscale frames; front standard deviation was about 27.6 and rear about 14.3. Native WeChat was reopened directly from `/usr/bin/wechat`. The user confirmed that both front and rear cameras could be selected and displayed a picture. This validates local native WeChat preview and switching; sustained calls, reboot persistence, rear autofocus and rear image quality remain unvalidated or unresolved.

The registration regression check can be run on Linux with `python3 tests/ipu4p-video-numbering.py /path/to/sp7-ipu4-camera/linux-6.19.8/drivers/media/pci/intel/ipu-isys-video.c`. It checks automatic numbering, the configured minimum, exhaustion fallback, invalid bounds and registration errors.

## Application bridge repair on 2026-10-25

The test Surface's active producer did not specify a camera and selected the rear sensor even for its front-named endpoint. The rear endpoint had no producer. `surface-camera-ondemand.c` now binds `/dev/video90` explicitly to `I2C2.CAMF` and `/dev/video91` to `I2C3.CAMR`, and shares a per-user hardware lock between the two producers. The IPU4P BE-SOC input is shared: front and rear cannot capture simultaneously. Switching waits for the previous consumer to close and a two-second release grace period.

Both endpoints use 1280x720. The earlier 640x480 request selected the rear sensor's 800x600 mode; the 720p request selects 1632x1224 instead. Native `cam` tests completed two opens at each resolution for each sensor, 120 frames per open. The repaired application endpoints then completed two alternating rounds of 180 buffers each through GStreamer V4L2. Every run's final 90 grayscale frame hashes were distinct, and both cameras had visible tonal variation. These are bounded capture/switching tests, not a sustained browser meeting qualification.

`ipa/simple/` contains the CC0-1.0 configuration files from [ruslanbay/ipu4-drivers](https://github.com/ruslanbay/ipu4-drivers/tree/upstream/configs/usr/share/libcamera/ipa/simple), Git blob IDs `962fa52679eadd2857a06caea3ff88c62b5b6bea` (front) and `3859f1965594abf58bfd40fd854c9096e372a9ac` (rear). The front matrices were derived upstream from Intel CPF data. The rear uses an identity matrix to expose saturation controls; it is not a calibrated rear-camera colour profile. Both configurations leave black-level measurement automatic. The services set `LIBCAMERA_IPA_CONFIG_PATH` to this private installation, leaving system libcamera data untouched.

The active Surface installation uses `surface-camera-ondemand-v5`, a front-service override and `surface-camera-rear.service`. Source templates are provided alongside this README. The previous service configuration is backed up in `/home/link/.cache/omarchy-surface-build/7.2.8-3.mBs2hJ/camera5-backup-20261025-001235`. No kernel or firmware was replaced for this repair.

Rear DW9719 focus control remains unavailable because its media entity has no device node. A separate module experiment was compiled but not installed: its bulk subdevice-node registration could race with device lifecycle operations and affect existing sensor nodes on failure. Fixing that properly requires further work in the IPU4P registration path. Do not treat these changes as autofocus support or Windows-equivalent rear image quality.

The earlier observations below describe the installation before this bridge repair.

On 2026-10-24, the pinned modules and modified OV5693 were rebuilt for `7.2.8-4-omarchy-bore-surface`. Both sensors passed three-frame raw capture with firmware authentication working. After disk hibernation, the ordinary desktop user captured 30 valid processed frames from each sensor; front frames contained normal tonal variation, while rear output remained nearly uniform and needs an illuminated, unobstructed-scene retest. Rear lens control is disabled because the DW9719 device has no V4L2 subdevice. Browser meetings and autofocus are not validated. The current kernel and power-test details are in [UPSTREAM.md](../kernel-bore/UPSTREAM.md).

The [sp7-ipu4-camera](https://github.com/georgemihaila/sp7-ipu4-camera) driver is validated upstream on Fedora 43 with linux-surface 6.19.8. Its Fedora installer cannot be used on Omarchy. This adapter builds its IPU4P modules and modified OV5693 front sensor against the exact adapted Omarchy kernel headers without installing or loading anything.

On the Surface Pro 7, while running the adapted kernel with matching headers:

```bash
git clone https://github.com/shaoya730/omarchy-surface-pro7.git
git clone https://github.com/georgemihaila/sp7-ipu4-camera.git
git -C sp7-ipu4-camera checkout aa0043f3649c3bff9247d5f99de5d164c3cdcc75
./omarchy-surface-pro7/camera/build.sh ./sp7-ipu4-camera
```

The scripts default to the running kernel. Set `KREL=7.2.8-4-omarchy-bore-surface` for build, installation, or rollback to target that installed kernel explicitly; `sudo` may require `sudo env KREL=...`. The legacy `7.2.5-6-omarchy` target remains supported. Each target needs its own rebuilt modules.

The five IPU4P modules are built inside the upstream checkout. The modified sensor is built at `sp7-ipu4-camera/ov5693-omarchy/ov5693.ko`. An earlier build against `7.2.5-5-omarchy` succeeded, but live firmware authentication failed with repeated DMA faults from IPU PCI device `8086:8a19`. The `7.2.5-6-omarchy` kernel patch adds that exact ID to the existing per-device IOMMU identity mapping quirk. On the test Surface Pro 7, firmware authentication succeeded and both RGB sensors delivered raw frames without a DMA fault. The first front frame was blank, and the rear was initially nearly black at its default exposure of 32. Temporarily increasing rear exposure to 1000 produced a much wider brightness range; the control was then restored to 32. The kernel's native `ipu_bridge` is used. The identity mapping reduces DMA isolation for this one IPU device; it does not change the global IOMMU setting.

Building alone does not make the camera usable. Runtime work requires `ipu4p_cpd.bin` extracted from Microsoft's Surface Pro 7 driver package, module installation, and capture tests for both cameras. The firmware verified for this build came from Microsoft's `SurfacePro7_Win11_22621_25.090.3489.0.msi` (valid Microsoft digital signature); its SHA-256 is `ff2c36cc81a5c726508b22970c2e2538ff06107dc5a72c93401403c227e5157f`. Do not commit or redistribute the Microsoft firmware. The modified OV5693 module shadows the existing kernel module; keep another bootable kernel available before testing. Rebuild the camera modules whenever the Omarchy kernel version changes.

To install the already built modules and a locally extracted firmware file (no reboot or module loading is performed):

```bash
sudo ./omarchy-surface-pro7/camera/install.sh ./sp7-ipu4-camera /path/to/ipu4p_cpd.bin
```

The installer records the five IPU4P modules and the OV5693 replacement in a hash-checked manifest. It uses the kernel's native `ipu_bridge`, does not enable upstream's experimental OV7251 options, leaves other kernel versions untouched, and does not rebuild the initramfs.

To load the installed modules and run bounded direct-capture checks, close applications using the cameras and run:

```bash
sudo modprobe -r ov5693 &&
sudo modprobe ov5693 &&
sudo timeout 30s modprobe intel-ipu4p-isys &&
sudo timeout 30s modprobe intel-ipu4p-psys

cd ./sp7-ipu4-camera
sudo ./test-capture.sh front
sudo ./test-capture.sh rear
```

Each capture command records three unpacked BG10 raw frames into `sp7-ipu4-camera/captures/`. On the test device, `front.raw` was 30,233,088 bytes (2592x1944) and `rear.raw` was 47,941,632 bytes (3264x2448). The initial rear frames stayed near black even in a bright scene and after a 12-frame warmup. A separate three-frame test at exposure 1000 increased rear-frame luminance from about 4114 to 4247 (16-bit raw scale) and expanded its range; exposure was restored immediately afterward. These checks support the direct raw capture path, **not** automatic exposure, image quality, processed video, or camera availability in desktop applications. Libcamera tools were not yet installed during these initial direct-capture tests. PipeWire's initial enumeration of the raw video nodes triggered repeated `v4l_enum_fmt` kernel warnings on this build; no new warnings occurred during the direct captures. Do not leave the experimental modules installed if this behavior is unacceptable.

### Application-layer progress

The same Omarchy test system subsequently installed Arch `libcamera`/`libcamera-tools` 0.7.2 and `pipewire-libcamera` 1.6.8, then restarted the user WirePlumber service. `cam -l` listed both sensors through Simple + SoftISP. The front camera passed three processed PPM captures and a release/reopen test. The rear generated processed frames, but the three-frame validator failed: one frame was all zero and the others were very dark at the low default exposure. PipeWire created front/rear libcamera video sources, and the front source delivered three non-black 640x480 RGB frames through `pipewiresrc`. These results do not yet qualify browser preview or conferencing. The test Chromium build contains the [PipeWire camera feature](https://chromium.googlesource.com/chromium/src/+/HEAD/media/capture/capture_switches.cc), which is disabled by default; browser testing uses the [WebRTC getUserMedia sample](https://webrtc.github.io/samples/src/content/getusermedia/gum/).

Chromium subsequently enumerated both cameras after enabling its PipeWire camera feature, but its front-camera preview remained blank/spinning. PipeWire showed a connected, running 640x480 RGBA stream from the front libcamera node to Chromium, so enumeration and portal access alone were not sufficient. A separate 15-frame PipeWire test completed, while a 120-frame test exited unsuccessfully under a 20-second cap. During the longer tests, the kernel repeatedly logged CSI-2 receiver error `0x4000` and `Ouch. Stream start failed.` on the OV5693 route; the messages stopped after capture ended. Do not use this build for browser meetings yet or leave a failing preview open: repeated capture attempts can flood the journal. The modules remain installed for investigation, but stable sustained capture and browser video are **not validated**.

On the same Surface, a later bounded front-camera test delivered 30 processed 640x480 frames at about 28.6 fps with WirePlumber stopped. After an application used the cameras, Chromium's front preview went blank again; with the application closed, `systemctl --user restart wireplumber` restored a live front image in a roughly five-second WebRTC sample test. This is a session recovery, **not** a driver fix or validation of a sustained browser meeting. A separate rear-camera attempt logged fatal CSI-2 errors (`0x88`/`0x80`), 31 failed sensor starts, and `Ouch. Stream start failed.` Avoid repeatedly opening a failing rear preview. Restarting WirePlumber can briefly interrupt audio and may require reselecting the previous audio profile.

To roll back:

```bash
cd ~
sudo ./omarchy-surface-pro7/camera/rollback.sh ./sp7-ipu4-camera
sudo reboot
```

Rollback retains the firmware file, as the upstream uninstaller does. If modules are already loaded, reboot after rollback to discard them from memory.
