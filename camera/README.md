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

The machine currently has no `ipu4p_cpd.bin` firmware and no camera device nodes. Building these modules alone does not make the camera usable. Runtime work still requires firmware extracted from Microsoft's Surface Pro 7 driver package, a carefully tracked module installation, and capture tests for both cameras. The modified OV5693 module would shadow the existing kernel module, so preserve the existing working kernel before testing it. Rebuild the camera modules whenever the Omarchy kernel version changes.
