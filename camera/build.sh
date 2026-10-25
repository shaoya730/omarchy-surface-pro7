#!/usr/bin/env bash
set -euo pipefail

kernel_release=${KREL:-$(uname -r)}
if [[ ! $kernel_release =~ ^7\.2\.8-[0-9]+-omarchy-bore-surface$ && $kernel_release != 7.2.5-6-omarchy ]]; then
  echo 'This build targets the Surface-adapted Omarchy kernel.' >&2
  exit 1
fi

source_dir=${1:?Usage: ./camera/build.sh /path/to/sp7-ipu4-camera}
source_dir=$(realpath -- "$source_dir")
expected_commit=aa0043f3649c3bff9247d5f99de5d164c3cdcc75
if [[ $(git -C "$source_dir" rev-parse HEAD) != "$expected_commit" ]]; then
  echo "Expected sp7-ipu4-camera commit $expected_commit" >&2
  exit 1
fi

kernel_dir=/lib/modules/$kernel_release/build
[[ $(make -s -C "$kernel_dir" kernelrelease) == "$kernel_release" ]] || {
  echo 'Kernel headers do not match the target release.' >&2; exit 1;
}
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
for camera_patch in ipu4p-video-numbering.patch ipu4p-rgb-notifier.patch; do
  patch_file=$script_dir/$camera_patch
  if patch --dry-run --batch --forward -d "$source_dir" -p1 < "$patch_file" >/dev/null 2>&1; then
    patch --batch --forward -d "$source_dir" -p1 < "$patch_file"
  elif ! patch --dry-run --batch --reverse -d "$source_dir" -p1 < "$patch_file" >/dev/null 2>&1; then
    echo "IPU4P patch does not match this source tree: $camera_patch" >&2
    exit 1
  fi
done
sensor_dir=$source_dir/ov5693-omarchy
KDIR=$kernel_dir KREL=$kernel_release "$source_dir/scripts/build-modules.sh" -j1
mkdir -p -- "$sensor_dir"
install -m644 "$script_dir/Makefile" "$sensor_dir/Makefile"
install -m644 "$source_dir/linux-6.19.8/drivers/media/i2c/ov5693.c" "$sensor_dir/ov5693.c"

make -C "$kernel_dir" M="$sensor_dir" -j1 modules
test "$(modinfo -F vermagic "$sensor_dir/ov5693.ko" | cut -d' ' -f1)" = "$kernel_release"
echo "IPU4P and OV5693 modules built for $kernel_release in $source_dir"
