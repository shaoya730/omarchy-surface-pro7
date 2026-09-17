#!/usr/bin/env bash
set -euo pipefail

product_name="$(cat /sys/class/dmi/id/product_name 2>/dev/null || true)"
if [[ $product_name != "Surface Pro 7" ]]; then
  printf 'This helper is for Surface Pro 7; detected: %s\n' "${product_name:-unknown}" >&2
  exit 1
fi

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
sudo install -d /etc/mkinitcpio.conf.d
# Limit Surface-only modules to kernels that provide the Surface drivers.
sudo tee /etc/mkinitcpio.conf.d/surface_device_modules.conf >/dev/null <<'EOF'
if [[ $KERNELVERSION == *-omarchy || $KERNELVERSION == *-surface ]]; then
  MODULES=(pinctrl_icelake surface_aggregator surface_aggregator_registry surface_aggregator_hub surface_hid_core surface_hid surface_kbd hid_surface ipts intel_lpss_pci 8250_dw)
fi
EOF
sudo install -Dm644 "$script_dir/surface/thermal-conf.xml" /etc/thermald/thermal-conf.xml

sudo mkinitcpio -P
if command -v systemctl >/dev/null 2>&1; then
  sudo systemctl enable --now thermald.service
fi

echo 'Surface Pro 7 initramfs and thermal configuration installed.'
