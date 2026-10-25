#!/usr/bin/env bash
set -euo pipefail

[[ $EUID == 0 ]] || { echo 'Run this script with sudo.' >&2; exit 1; }
source_dir=$(realpath -- "${1:?Usage: sudo ./camera/rollback.sh /path/to/sp7-ipu4-camera}")
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
expected_commit=aa0043f3649c3bff9247d5f99de5d164c3cdcc75
[[ $(git -c safe.directory="$source_dir" -C "$source_dir" rev-parse HEAD) == "$expected_commit" ]] || {
  echo "Expected sp7-ipu4-camera commit $expected_commit" >&2
  exit 1
}

kernel_release=${KREL:-$(uname -r)}
[[ $kernel_release =~ ^7\.2\.8-[0-9]+-omarchy-bore-surface$ || $kernel_release == 7.2.5-6-omarchy ]] || { echo 'Wrong target kernel.' >&2; exit 1; }
KREL=$kernel_release \
  MODPROBE_CONFIG=/lib/modules/$kernel_release/updates/extra/.ipu4p-ov7251-unused.conf \
  MODULE_SOURCE_MANIFEST_EXTRA="$script_dir/ipu4p-omarchy.modules" \
  "$source_dir/scripts/uninstall-modules.sh"
echo 'Reboot to unload any camera modules still resident in memory. Firmware was retained.'
