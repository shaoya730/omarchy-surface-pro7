#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
check_kernel() (
  KERNELVERSION=$1
  MODULES=(existing_module)
  source "$repo_dir/surface/mkinitcpio.conf"
  [[ ${MODULES[0]} == existing_module ]]
  if [[ $2 == surface ]]; then
    [[ " ${MODULES[*]} " == *' ipts '* ]]
    [[ " ${MODULES[*]} " == *' hid_surface '* ]]
    [[ " ${MODULES[*]} " == *' pinctrl_icelake '* ]]
  else
    [[ ${#MODULES[@]} == 1 ]]
  fi
)

check_kernel 7.2.8-3-omarchy-bore-surface surface
check_kernel 7.2.8-2-omarchy-bore-surface surface
check_kernel 7.2.8-1-omarchy-bore-surface surface
check_kernel 7.2.5-6-omarchy surface
check_kernel 7.2.8-9-omarchy stock
check_kernel 6.12.55-1-lts stock
printf 'Surface initramfs configuration checks passed.\n'
