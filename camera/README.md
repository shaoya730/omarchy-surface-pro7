# Experimental Surface Pro 7 IPU4P build

The [sp7-ipu4-camera](https://github.com/georgemihaila/sp7-ipu4-camera) driver is validated upstream on Fedora 43 with linux-surface 6.19.8. Its Fedora installer cannot be used on Omarchy. This adapter builds its IPU4P modules and modified OV5693 front sensor against the exact `7.2.5-6-omarchy` headers without installing or loading anything.

On the Surface Pro 7, while running `7.2.5-6-omarchy` with matching headers:

```bash
git clone https://github.com/shaoya730/omarchy-surface-pro7.git
git clone https://github.com/georgemihaila/sp7-ipu4-camera.git
git -C sp7-ipu4-camera checkout aa0043f3649c3bff9247d5f99de5d164c3cdcc75
./omarchy-surface-pro7/camera/build.sh ./sp7-ipu4-camera
```

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
