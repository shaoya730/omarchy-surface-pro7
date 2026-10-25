"""Exercise the prepared kernel's OV8865 stream callback with device-call stubs.

Set KERNEL_SOURCE to a patched kernel tree and run with a C compiler available.
"""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


@unittest.skipUnless(os.environ.get("KERNEL_SOURCE"), "set KERNEL_SOURCE to a prepared kernel tree")
class Ov8865StreamTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        driver = (Path(os.environ["KERNEL_SOURCE"]) / "drivers/media/i2c/ov8865.c").read_text()
        start = driver.index("static int ov8865_s_stream(")
        end = driver.index("\n}\n", start) + 3
        callback = driver[start:end]
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        source = Path(cls.temp.name) / "stream.c"
        cls.executable = Path(cls.temp.name) / "stream-test"
        source.write_text(r'''
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
struct v4l2_subdev { int unused; };
struct ov8865_state { bool streaming; };
struct ov8865_sensor {
    struct ov8865_state state;
    void *dev;
    int mutex;
    struct { int handler; } ctrls;
};
static struct ov8865_sensor sensor;
static int references, put_count, init_error, controls_error, standby_error;
static char events[32];
static void event(char value) { size_t n = strlen(events); events[n] = value; events[n + 1] = 0; }
static struct ov8865_sensor *ov8865_subdev_sensor(struct v4l2_subdev *subdev) { return &sensor; }
static int pm_runtime_resume_and_get(void *dev) { references++; event('G'); return 0; }
static void pm_runtime_put(void *dev) { references--; put_count++; event('P'); }
static void mutex_lock(int *mutex) {}
static void mutex_unlock(int *mutex) {}
static int ov8865_sensor_init(struct ov8865_sensor *sensor) { event('I'); return init_error; }
static int __v4l2_ctrl_handler_setup(int *handler) { event('C'); return controls_error; }
static int ov8865_sw_standby(struct ov8865_sensor *sensor, bool standby) { event('S'); return standby_error; }
''' + callback + r'''
#define CHECK(value) do { if (!(value)) { fprintf(stderr, "failed: %s; events=%s refs=%d put_count=%d\n", #value, events, references, put_count); return 1; } } while (0)
int main(int argc, char **argv) {
    struct v4l2_subdev subdev;
    int scenario = atoi(argv[1]);
    int ret;
    if (scenario == 0) {
        /* An already powered sensor must still get its negotiated mode. */
        ret = ov8865_s_stream(&subdev, 1);
        CHECK(ret == 0 && sensor.state.streaming && references == 1);
        CHECK(strcmp(events, "GICS") == 0);
    } else if (scenario == 1 || scenario == 2 || scenario == 3) {
        if (scenario == 1) init_error = -5;
        if (scenario == 2) controls_error = -5;
        if (scenario == 3) standby_error = -5;
        ret = ov8865_s_stream(&subdev, 1);
        CHECK(ret == -5 && !sensor.state.streaming && references == 0 && put_count == 1);
        if (scenario == 1) CHECK(strcmp(events, "GIP") == 0);
        if (scenario == 2) CHECK(strcmp(events, "GICP") == 0);
    } else {
        references = 1;
        sensor.state.streaming = true;
        if (scenario == 5) standby_error = -5;
        ret = ov8865_s_stream(&subdev, 0);
        CHECK(references == 0 && put_count == 1 && strcmp(events, "SP") == 0);
        CHECK(ret == (scenario == 5 ? -5 : 0));
        CHECK(sensor.state.streaming == (scenario == 5));
    }
    return 0;
}
''')
        result = subprocess.run([os.environ.get("CC", "cc"), "-std=c11", str(source), "-o", str(cls.executable)],
                                text=True, capture_output=True)
        if result.returncode:
            raise RuntimeError(result.stderr)

    def run_scenario(self, scenario):
        result = subprocess.run([str(self.executable), str(scenario)], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_already_powered_sensor_gets_mode_and_controls(self):
        self.run_scenario(0)

    def test_init_failure_releases_power_reference(self):
        self.run_scenario(1)

    def test_controls_failure_releases_power_reference(self):
        self.run_scenario(2)

    def test_stream_start_failure_releases_power_reference(self):
        self.run_scenario(3)

    def test_stream_stop_releases_power_reference(self):
        self.run_scenario(4)

    def test_stream_stop_failure_releases_reference_and_keeps_state(self):
        self.run_scenario(5)
