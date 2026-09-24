#!/usr/bin/env bash
set -euo pipefail

[[ $EUID == 0 ]] || { echo 'Run this script with sudo.' >&2; exit 1; }
[[ $(uname -r) == 7.2.5-6-omarchy ]] || { echo 'Wrong running kernel.' >&2; exit 1; }

source_dir=$(realpath -- "${1:?Usage: sudo ./camera/install.sh /path/to/sp7-ipu4-camera /path/to/ipu4p_cpd.bin}")
firmware=$(realpath -- "${2:?Firmware path required}")
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
expected_commit=aa0043f3649c3bff9247d5f99de5d164c3cdcc75
[[ $(git -c safe.directory="$source_dir" -C "$source_dir" rev-parse HEAD) == "$expected_commit" ]] || {
  echo "Expected sp7-ipu4-camera commit $expected_commit" >&2
  exit 1
}
[[ -s $firmware ]] || { echo 'Firmware is missing or empty.' >&2; exit 1; }
expected_firmware_hash=ff2c36cc81a5c726508b22970c2e2538ff06107dc5a72c93401403c227e5157f
[[ $(sha256sum "$firmware" | cut -d' ' -f1) == "$expected_firmware_hash" ]] || {
  echo 'Firmware does not match the Microsoft Surface Pro 7 package verified for this build.' >&2
  exit 1
}
[[ -f $source_dir/ov5693-omarchy/ov5693.ko ]] || { echo 'Build the modules first.' >&2; exit 1; }

FIRMWARE="$firmware" KREL=7.2.5-6-omarchy \
  MODPROBE_CONFIG=/lib/modules/7.2.5-6-omarchy/updates/extra/.ipu4p-ov7251-unused.conf \
  MODPROBE_SOURCE="$script_dir/unused-ov7251.conf" \
  MODULE_SOURCE_MANIFEST_EXTRA="$script_dir/ipu4p-omarchy.modules" \
  "$source_dir/scripts/install-modules.sh"

modinfo -k 7.2.5-6-omarchy -n intel-ipu4p
modinfo -k 7.2.5-6-omarchy -n ov5693
echo 'Installed on disk. No modules were loaded and no initramfs or boot entry was changed.'
