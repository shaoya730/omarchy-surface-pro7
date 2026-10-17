# Omarchy on Surface Pro 7

This repository builds an Omarchy Linux 7.2.8 BORE kernel with the Surface Pro 7 support that is missing from the stock Omarchy kernel:

- Intel IPTS touchscreen support, including the Ice Lake MEI and IOMMU quirks
- Surface Type Cover and Surface HID fixes
- Surface Pro 7 camera sensor and IPU IOMMU fixes (IPU4P driver is separate)
- TPS68470 camera LED support
- `iptsd`, the userspace touch and stylus daemon
- Surface Pro 7 thermal and initramfs setup

The `kernel-bore/` package is based on Omarchy's `linux-omarchy-bore` 7.2.8-7 sources and patches, then applies the Surface changes. It uses a separate package name so the official kernel can remain installed as a boot fallback. It is intended for an Intel Surface Pro 7, not the Pro 7+.

## Build and install

Run these commands on the Surface Pro 7 or another Arch Linux x86_64 system:

```bash
git clone https://github.com/shaoya730/omarchy-surface-pro7.git
cd omarchy-surface-pro7

cd kernel-bore
makepkg -s
sudo pacman -U ./linux-omarchy-bore-surface-7.2.8-1-x86_64.pkg.tar.zst \
  ./linux-omarchy-bore-surface-headers-7.2.8-1-x86_64.pkg.tar.zst

cd ../iptsd
makepkg -si

cd ..
./install-surface-pro7.sh
```

Keep the existing working kernel in the boot menu until the new kernel has been tested. The build can take a while and needs several gigabytes of free disk space. The separately built IPU4P camera modules from `camera/` target the old `7.2.5-6-omarchy` kernel and will not work on this new kernel without a separate rebuild and validation; do not remove the working kernel if you depend on those cameras.

After rebooting, verify the new kernel and Surface modules:

```bash
uname -r
lsmod | grep -E 'ipts|surface'
journalctl -b -k | grep -Ei 'ipts|surface|ipu'
```

`iptsd` is started automatically by its udev rule when the IPTS touchscreen appears.

## Repository layout

- `kernel-bore/` — current `linux-omarchy-bore-surface` 7.2.8 PKGBUILD, Omarchy BORE patches, Surface Pro 7 patch, and x86_64 config
- `kernel/` — previous `linux-omarchy` 7.2.5-6 build, retained for reference/rollback
- `iptsd/` — Arch PKGBUILD for the official linux-surface `iptsd` v3.1.0 release
- `surface/` — Surface Pro 7 thermald configuration
- `camera/` — experimental IPU4P module build for `7.2.5-6-omarchy`; see [camera/README.md](camera/README.md)
- `install-surface-pro7.sh` — initramfs and thermal configuration helper

The actual kernel compilation and boot test must be performed on Arch Linux. Do not assume the new version works until the complete patch application, build, and hardware tests pass.
