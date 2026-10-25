# Native WeChat camera crash investigation

Status: diagnosed; no WeChat program file has been modified.

## Observed failure

On the test Surface Pro 7, native `wechat-bin 4.1.13.26-1` aborted at
2026-10-25 15:58:25 CST when starting camera capture. The system core identifies
PID 6005, TID 6549 (`CaptureThread`), signal SIGABRT. The application was started
normally as `/usr/bin/wechat`, executable `/opt/wechat/wechat`.

The fatal message recovered from the abort frame is:

```text
Fatal error in: .../third_party/webrtc/modules/video_capture/linux/video_capture_v4l2.cc, line 416
last system error: 1
Check failed: !race_checker416.RaceDetected()
```

The `last system error` field is not by itself evidence of a failed device ioctl.
The actual fatal condition is the serial-execution checker. The faulting thread
aborted at capture-process entry, before its device select loop.

## Independent system checks

The preceding reboot preserved the custom kernel, ISYS firmware-port mask 64,
processed video0/1, raw video64+, both RGB sensors and the DW9719 lens devnode.
An unrelated startup ACL timing failure in the two user producer services was
repaired with on-failure retries. Both services now stay active and recover from
an unexpected exit in about 5.2 seconds.

Front/rear endpoint captures returned live frames. A 900-frame processed rear
capture completed in 34.6 seconds, with brightness settling and focus position
272. These checks do not qualify native WeChat preview: the application crash
is still unresolved.

## Upstream match

WebRTC commit
[`c420a240e19e02026f7dfec1261acc4153f1a1ff`](https://webrtc.googlesource.com/src/+/c420a240e19e02026f7dfec1261acc4153f1a1ff),
dated 2026-04-21, fixes the capture check's scope before thread creation:
the capture checker must be released before the capture thread starts, since
that thread immediately acquires the same checker. A sufficiently fast thread
start otherwise trips the check. Upstream issue: `webrtc:504490094`; review:
[`465581`](https://webrtc-review.googlesource.com/c/src/+/465581).

Read-only disassembly of the installed WeChat corroborates the old order:

- CaptureProcess enters the checker at virtual address `0x88b2d99`, tests it,
  and reaches the fatal line-416 path at `0x88b301b` when the check fails.
- StartCapture creates the thread via the call at `0x88b26c3`.
- Its checker is only released later in the common epilogue, via the call at
  `0x88b20fe` to `0x88b1700`. The release decrements the counter referenced by
  its scope object; the capture path uses the corresponding object member.

This is a strong match to the upstream startup race. A kernel scheduling change
could change how often it reproduces, but cannot correct the application's
checker lifetime. No scheduling workaround or per-app camera namespace is used.

## Decision and evidence report

The vendor homepage's current x86_64 DEB link was checked directly with a
bounded HTTP Range request. Its control archive reports `Version: 4.1.13.26`,
matching the installed release. Thus that official download does not offer a
newer version to test. The upstream patch was also fetched from the official
Git repository and confirms that both the capture lock and serial checker leave
scope before thread creation; it does not merely disable the fatal check.

No official WeChat release containing this particular fix has been confirmed.
WeChat does not provide this application's buildable source. Backporting the
fix locally would require a separately validated binary modification; simply
removing the fatal check is not an implementation of the upstream fix. Any
candidate must preserve actual serialization checks, verify the exact original
binary hash, be tested independently and retain a complete original-file
rollback before replacement. The user chose to retain the official WeChat
program and collect evidence; no binary patch will be attempted under this task.

The [Chinese report](../reports/wechat-camera-20261025/报告.md) includes the
abbreviated crash stack, exact package versions and executable hash. The final
package integrity check reports 197 files and zero altered files. It also records
the separately confirmed front-preview mirroring: reference preview text is
readable, only WeChat's local preview reverses it, and outgoing orientation is
not verified. No global front flip is applied. The evidence has not been sent
to any external service.

The core remains on the Surface. Only the relevant fatal message and code
analysis are recorded here; no camera images or core memory are included.
