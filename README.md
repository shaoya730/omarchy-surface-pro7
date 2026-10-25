# Omarchy on Surface Pro 7

This repository builds an Omarchy Linux 7.2.8 BORE kernel with the Surface Pro 7 support that is missing from the stock Omarchy kernel:

- Intel IPTS touchscreen support, including the Ice Lake MEI and IOMMU quirks
- Surface Type Cover and Surface HID fixes
- Surface Pro 7 camera sensor and IPU IOMMU fixes (IPU4P driver is separate)
- TPS68470 camera LED support
- `iptsd`, the userspace touch and stylus daemon
- Surface Pro 7 thermal and initramfs setup

The `kernel-bore/` package is based on Omarchy's `linux-omarchy` 7.2.8-9 sources and patches, then applies the Surface changes. The adapted package is `linux-omarchy-bore-surface` 7.2.8-4. It keeps its existing separate package name so the official kernel can remain installed as a boot fallback. It is intended for an Intel Surface Pro 7, not the Pro 7+.

Upstream now builds BORE directly as `linux-omarchy`; its old `linux-omarchy-bore` package only transitions users to that name. This repository keeps the `kernel-bore/` directory and adapted package name for upgrades from 7.2.8-1 and 7.2.8-2. Revision 3 incorporates linux-surface's IPTS report-size correction, builds Ice Lake pin control into the kernel, and includes its two OV8865 rear-camera stream/power-management fixes. Revision 4 validates SoundWire firmware link counts before constructing their masks, fixing a UBSAN shift report on the Pro 7. See [kernel-bore/UPSTREAM.md](kernel-bore/UPSTREAM.md) for the pinned upstream revisions and local changes.

## Build and install

Run these commands on the Surface Pro 7 or another Arch Linux x86_64 system:

```bash
git clone https://github.com/shaoya730/omarchy-surface-pro7.git
cd omarchy-surface-pro7

cd kernel-bore
makepkg -s
sudo pacman -U ./linux-omarchy-bore-surface-7.2.8-4-x86_64.pkg.tar.zst \
  ./linux-omarchy-bore-surface-headers-7.2.8-4-x86_64.pkg.tar.zst

cd ../iptsd
makepkg -si

cd ..
./install-surface-pro7.sh
```

Keep the existing working kernel in the boot menu until the new kernel has been tested. The build can take a while and needs several gigabytes of free disk space. The separately built IPU4P camera modules from `camera/` must be rebuilt against the exact new kernel and matching headers before camera tests. The adapters accept `KREL` to target an installed adapted kernel explicitly.

After rebooting, verify the new kernel and Surface modules:

```bash
uname -r
lsmod | grep -E 'ipts|surface'
journalctl -b -k | grep -Ei 'ipts|surface|ipu'
```

`iptsd` is started automatically by its udev rule when the IPTS touchscreen appears.

The initramfs helper appends Surface modules only for kernels ending in `-surface` and the previous adapted `7.2.5-6-omarchy` kernel. The official `7.2.8-9-omarchy` fallback keeps its normal module configuration.

## Repository layout

- `kernel-bore/` — current `linux-omarchy-bore-surface` 7.2.8-4 PKGBUILD, Omarchy BORE patches, Surface Pro 7 patch, x86_64 config, and upstream signing keys
- `kernel/` — previous `linux-omarchy` 7.2.5-6 build, retained for reference/rollback
- `iptsd/` — Arch PKGBUILD for the official linux-surface `iptsd` v3.1.0 release
- `surface/` — Surface Pro 7 thermald configuration
- `camera/` — experimental IPU4P module build for the adapted Omarchy kernel; see [camera/README.md](camera/README.md)
- `install-surface-pro7.sh` — initramfs and thermal configuration helper
- `tests/surface-initramfs.sh` — checks that adapted kernels get Surface modules and stock kernels keep their existing modules
- `tests/test_ipts_descriptor.py` — checks the synthesized input report length against the fallback HID descriptor
- `tests/test_soundwire_acpi.py` — runs the actual prepared SoundWire ACPI callbacks and mask macro under UBSAN; requires `KERNEL_SOURCE` and a C compiler
- `tests/test_ov8865_stream.py` — exercises the prepared kernel's rear-camera stream callback; requires `KERNEL_SOURCE` and a C compiler

The complete package build and boot test must be performed on Arch Linux. Do not assume the new version works until the build and hardware tests pass. After booting, test touchscreen and pen input, Type Cover input and backlight, detaching and reattaching the cover, suspend/resume, and thermal behavior. Camera support still requires the separate IPU4P driver work described above.
