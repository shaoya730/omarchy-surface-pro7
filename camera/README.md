# Experimental Surface Pro 7 IPU4P build

The [sp7-ipu4-camera](https://github.com/georgemihaila/sp7-ipu4-camera) driver is validated upstream on Fedora 43 with linux-surface 6.19.8. Its Fedora installer cannot be used on Omarchy. This adapter builds its IPU4P modules and modified OV5693 front sensor against the exact `7.2.5-5-omarchy` headers without installing or loading anything.

On the Surface Pro 7, while running `7.2.5-5-omarchy` with matching headers:

```bash
git clone https://github.com/shaoya730/omarchy-surface-pro7.git
git clone https://github.com/georgemihaila/sp7-ipu4-camera.git
git -C sp7-ipu4-camera checkout aa0043f3649c3bff9247d5f99de5d164c3cdcc75
./omarchy-surface-pro7/camera/build.sh ./sp7-ipu4-camera
```

The six IPU4P modules are built inside the upstream checkout. The modified sensor is built at `sp7-ipu4-camera/ov5693-omarchy/ov5693.ko`. Both builds and their `vermagic` checks succeeded on the Surface Pro 7 with `7.2.5-5-omarchy` on 2026-09-25. The kernel's existing `ipu_bridge` is available, but runtime compatibility has not yet been verified.

Building alone does not make the camera usable. Runtime work requires `ipu4p_cpd.bin` extracted from Microsoft's Surface Pro 7 driver package, module installation, and capture tests for both cameras. The firmware verified for this build came from Microsoft's `SurfacePro7_Win11_22621_25.090.3489.0.msi` (valid Microsoft digital signature); its SHA-256 is `ff2c36cc81a5c726508b22970c2e2538ff06107dc5a72c93401403c227e5157f`. Do not commit or redistribute the Microsoft firmware. The modified OV5693 module shadows the existing kernel module; keep another bootable kernel available before testing. Rebuild the camera modules whenever the Omarchy kernel version changes.

To install the already built modules and a locally extracted firmware file (no reboot or module loading is performed):

```bash
sudo ./omarchy-surface-pro7/camera/install.sh ./sp7-ipu4-camera /path/to/ipu4p_cpd.bin
```

The installer records the five IPU4P modules and the OV5693 replacement in a hash-checked manifest. It uses the kernel's native `ipu_bridge`, leaves other kernel versions untouched, and does not rebuild the initramfs. To remove only the unchanged installed modules and restore the original OV5693 on the next boot:

```bash
sudo ./omarchy-surface-pro7/camera/rollback.sh ./sp7-ipu4-camera
sudo reboot
```

Rollback retains the firmware file, as the upstream uninstaller does. If modules are already loaded, reboot after rollback to discard them from memory.
