#!/usr/bin/env bash
set -euo pipefail

product_name="$(cat /sys/class/dmi/id/product_name 2>/dev/null || true)"
if [[ $product_name != "Surface Pro 7" ]]; then
  printf 'This helper is for Surface Pro 7; detected: %s\n' "${product_name:-unknown}" >&2
  exit 1
fi

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
sudo install -Dm644 "$script_dir/surface/mkinitcpio.conf" /etc/mkinitcpio.conf.d/surface_device_modules.conf
sudo install -Dm644 "$script_dir/surface/thermal-conf.xml" /etc/thermald/thermal-conf.xml

if command -v limine-mkinitcpio >/dev/null 2>&1; then
  sudo limine-mkinitcpio
else
  sudo mkinitcpio -P
fi
if command -v systemctl >/dev/null 2>&1; then
  sudo systemctl enable --now thermald.service
fi

echo 'Surface Pro 7 initramfs and thermal configuration installed.'
