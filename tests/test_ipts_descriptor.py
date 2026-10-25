"""Check that synthesized IPTS input reports satisfy their HID descriptor."""

from collections import defaultdict
from pathlib import Path
import re
import unittest


class IptsDescriptorTest(unittest.TestCase):
    def test_data_report_matches_fallback_descriptor(self):
        patch = (Path(__file__).resolve().parents[1] / "kernel-bore" /
                 "0900-surface-pro7.patch").read_text()
        section = patch.split("+++ b/drivers/hid/ipts/desc.h\n", 1)[1]
        section = section.split("diff --git ", 1)[0]
        source = "\n".join(line[1:] for line in section.splitlines()
                           if line.startswith("+"))
        report_id = int(re.search(r"#define IPTS_HID_REPORT_DATA\s+(\d+)", source)[1])
        sent_size = int(re.search(r"#define IPTS_HID_REPORT_DATA_SIZE\s+(\d+)", source)[1])
        descriptor = source.split("ipts_fallback_descriptor[] = {", 1)[1].split("};", 1)[0]
        descriptor = re.sub(r"/\*.*?\*/", "", descriptor, flags=re.S)
        data = bytes(int(value, 16) for value in re.findall(r"0x[0-9A-Fa-f]+", descriptor))

        # HID short items encode size, type and tag in the prefix byte.
        report_size = report_count = current_id = 0
        input_bits = defaultdict(int)
        offset = 0
        while offset < len(data):
            prefix = data[offset]
            size = (0, 1, 2, 4)[prefix & 3]
            value = int.from_bytes(data[offset + 1:offset + 1 + size], "little")
            item_type, tag = (prefix >> 2) & 3, prefix >> 4
            if item_type == 1:  # Global: Report Size, Report ID, Report Count.
                if tag == 7:
                    report_size = value
                elif tag == 8:
                    current_id = value
                elif tag == 9:
                    report_count = value
            elif item_type == 0 and tag == 8:  # Main: Input.
                input_bits[current_id] += report_size * report_count
            offset += size + 1

        self.assertIn(report_id, input_bits)
        required_size = (input_bits[report_id] + 7) // 8 + bool(report_id)
        self.assertEqual(sent_size, required_size,
                         "Synthesized report omits bytes declared by the fallback HID descriptor")


if __name__ == "__main__":
    unittest.main()
