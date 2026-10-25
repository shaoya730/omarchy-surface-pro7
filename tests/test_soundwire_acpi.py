"""Exercise the prepared kernel's SoundWire ACPI scan with UBSAN enabled.

Set KERNEL_SOURCE to a kernel tree and run with a C compiler available. The
test extracts the actual scan and link-selection functions plus GENMASK_TYPE;
only firmware/device services are stubbed. It never changes KERNEL_SOURCE.
"""

import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest


@unittest.skipUnless(os.environ.get("KERNEL_SOURCE"), "set KERNEL_SOURCE to a prepared kernel tree")
class SoundwireAcpiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        kernel = Path(os.environ["KERNEL_SOURCE"])
        driver = (kernel / "sound/hda/core/intel-sdw-acpi.c").read_text()
        start = driver.index("static bool is_link_enabled(")
        end = driver.index("\nstatic acpi_status", start)
        callbacks = driver[start:end]
        bits = (kernel / "include/linux/bits.h").read_text()
        genmask = re.search(r"^#define GENMASK_TYPE\(t, h, l\).*?(?=\n\n)",
                            bits, re.MULTILINE | re.DOTALL).group()
        genmask += "\n" + re.search(r"^#define GENMASK\(h, l\).*GENMASK_TYPE.*$",
                                     bits, re.MULTILINE).group()
        genmask += "\n" + "\n".join(re.search(r"^#define " + name + r"\b.*$", bits, re.MULTILINE).group()
                                      for name in ("BITS_PER_BYTE", "BITS_PER_TYPE"))
        header = (kernel / "include/linux/soundwire/sdw_intel.h").read_text()
        constants = "\n".join(re.search(r"^#define " + name + r"\s+.*$", header, re.MULTILINE).group()
                              for name in ("SDW_INTEL_MAX_LINKS", "SDW_INTEL_QUIRK_MASK_BUS_DISABLE"))
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        source = Path(cls.temp.name) / "soundwire.c"
        cls.executable = Path(cls.temp.name) / "soundwire-test"
        source.write_text(r'''
#include <stdbool.h>
#include <stdint.h>
#include <limits.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef uint8_t u8;
typedef uint32_t u32;
#define BIT(n) (1UL << (n))
/* The function uses runtime bounds, so the compile-time input check is zero.
 * GENMASK_TYPE below is extracted intact; its type_max is unsigned long. */
#define GENMASK_INPUT_CHECK(h, l) 0
#define type_max(t) ((t)~(t)0)
''' + genmask + "\n" + constants + r'''
#define for_each_set_bit(i, addr, size) \
    for ((i) = 0; (i) < (size); (i)++) if (*(addr) & BIT(i))
#define dev_err(...) ((void)0)
#define dev_warn(...) ((void)0)
#define dev_dbg(...) ((void)0)
struct fwnode_handle { unsigned int index; };
struct acpi_device { int dev; };
struct sdw_intel_acpi_info { void *handle; int count; u32 link_mask; };
static struct acpi_device device;
static struct fwnode_handle controller, links[32];
static bool have_device = true;
static u32 master_count, manager_list, present_links = 0xffffffffU, disabled_links;
static int manager_error = -EINVAL, master_error, master_reads;
static int ctrl_link_mask;
static struct acpi_device *acpi_fetch_acpi_dev(void *handle)
{ return have_device ? &device : NULL; }
static struct fwnode_handle *acpi_fwnode_handle(struct acpi_device *adev)
{ return &controller; }
static unsigned int hweight32(u32 value) { return __builtin_popcount(value); }
static int fwnode_property_read_u32(struct fwnode_handle *node, const char *name, u32 *value)
{
    if (!strcmp(name, "mipi-sdw-manager-list")) {
        if (!manager_error) *value = manager_list;
        return manager_error;
    }
    if (!strcmp(name, "mipi-sdw-master-count")) {
        master_reads++;
        if (!master_error) *value = master_count;
        return master_error;
    }
    if (!strcmp(name, "intel-quirk-mask")) {
        *value = (disabled_links & BIT(node->index)) ? SDW_INTEL_QUIRK_MASK_BUS_DISABLE : 0;
        return 0;
    }
    abort();
}
static struct fwnode_handle *fwnode_get_named_child_node(struct fwnode_handle *node, const char *name)
{
    unsigned int index;
    if (sscanf(name, "mipi-sdw-link-%u-subproperties", &index) != 1 || index >= 32) abort();
    if (!(present_links & BIT(index))) return NULL;
    links[index].index = index;
    return &links[index];
}
static void fwnode_handle_put(struct fwnode_handle *node) {}
''' + callbacks + r'''
#define CHECK(value) do { if (!(value)) { fprintf(stderr, "failed: %s\n", #value); return 1; } } while (0)
int main(int argc, char **argv)
{
    struct sdw_intel_acpi_info info = { .count = -1, .link_mask = 0xdeadbeef };
    const char *scenario = argv[1];
    int ret;
    if (!strcmp(scenario, "count")) {
        master_count = strtoul(argv[2], NULL, 0);
    } else if (!strcmp(scenario, "manager")) {
        manager_error = 0;
        manager_list = strtoul(argv[2], NULL, 0);
        master_error = -EIO; /* A valid manager-list must never fall back. */
    } else if (!strcmp(scenario, "selection")) {
        master_count = 5;
        present_links = 0x1b; /* Link 2 has no firmware child. */
        disabled_links = 0x02; /* Link 1 has the bus-disable quirk. */
        ctrl_link_mask = 0x0f; /* The module parameter excludes link 4. */
    } else if (!strcmp(scenario, "read-error")) {
        master_error = -EIO;
    } else if (!strcmp(scenario, "no-device")) {
        have_device = false;
    } else {
        abort();
    }
    ret = sdw_intel_scan_controller(&info);
    CHECK(ret == strtol(argv[3], NULL, 0));
    if (ret) {
        CHECK(info.count == -1 && info.link_mask == 0xdeadbeef);
    } else {
        CHECK(info.count == strtol(argv[4], NULL, 0));
        CHECK(info.link_mask == strtoul(argv[5], NULL, 0));
    }
    if (!strcmp(scenario, "manager") || !strcmp(scenario, "no-device"))
        CHECK(master_reads == 0);
    else
        CHECK(master_reads == 1);
    return 0;
}
''')
        result = subprocess.run([os.environ.get("CC", "cc"), "-std=c11", "-O1",
                                 "-fsanitize=undefined", "-fno-sanitize-recover=undefined",
                                 str(source), "-o", str(cls.executable)], text=True, capture_output=True)
        if result.returncode:
            raise RuntimeError(result.stderr)

    def run_scenario(self, scenario, value, result, count=0, mask=0):
        process = subprocess.run([str(self.executable), scenario, str(value), str(result),
                                  str(count), str(mask)], text=True, capture_output=True)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(process.stderr, "")

    def test_zero_master_count_is_rejected_without_undefined_shift(self):
        self.run_scenario("count", 0, -22)

    def test_oversized_master_counts_are_rejected_without_undefined_shift(self):
        for count in (6, 64, 65, 0xffffffff):
            with self.subTest(count=count):
                self.run_scenario("count", count, -22)

    def test_valid_master_counts_enable_contiguous_links(self):
        for count, mask in ((1, 0x01), (2, 0x03), (3, 0x07), (4, 0x0f), (5, 0x1f)):
            with self.subTest(count=count):
                self.run_scenario("count", count, 0, count, mask)

    def test_manager_list_preserves_sparse_links_and_does_not_read_master_count(self):
        self.run_scenario("manager", 0x15, 0, 3, 0x15)

    def test_empty_manager_list_is_rejected_without_falling_back(self):
        self.run_scenario("manager", 0, -22)

    def test_oversized_manager_list_is_rejected(self):
        self.run_scenario("manager", 0x3f, -22)

    def test_firmware_quirk_and_module_mask_still_select_links(self):
        self.run_scenario("selection", 0, 0, 5, 0x09)

    def test_master_count_read_error_is_preserved(self):
        self.run_scenario("read-error", 0, -5)

    def test_missing_acpi_device_is_rejected(self):
        self.run_scenario("no-device", 0, -22)


if __name__ == "__main__":
    unittest.main()
