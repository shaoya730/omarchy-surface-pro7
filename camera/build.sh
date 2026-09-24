#!/usr/bin/env bash
set -euo pipefail

if [[ $(uname -r) != 7.2.5-6-omarchy ]]; then
  echo 'This build targets the installed 7.2.5-6-omarchy kernel.' >&2
  exit 1
fi

source_dir=${1:?Usage: ./camera/build.sh /path/to/sp7-ipu4-camera}
source_dir=$(realpath -- "$source_dir")
expected_commit=aa0043f3649c3bff9247d5f99de5d164c3cdcc75
if [[ $(git -C "$source_dir" rev-parse HEAD) != "$expected_commit" ]]; then
  echo "Expected sp7-ipu4-camera commit $expected_commit" >&2
  exit 1
fi

kernel_dir=/lib/modules/7.2.5-6-omarchy/build
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
sensor_dir=$source_dir/ov5693-omarchy
mkdir -p -- "$sensor_dir"
install -m644 "$script_dir/Makefile" "$sensor_dir/Makefile"
install -m644 "$source_dir/linux-6.19.8/drivers/media/i2c/ov5693.c" "$sensor_dir/ov5693.c"

KDIR=$kernel_dir KREL=7.2.5-6-omarchy "$source_dir/scripts/build-modules.sh" -j1
make -C "$kernel_dir" M="$sensor_dir" -j1 modules
test "$(modinfo -F vermagic "$sensor_dir/ov5693.ko" | cut -d' ' -f1)" = 7.2.5-6-omarchy
echo "IPU4P and OV5693 modules built for 7.2.5-6-omarchy in $source_dir"
