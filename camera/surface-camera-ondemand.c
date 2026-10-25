#define _GNU_SOURCE

#include <ctype.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/videodev2.h>
#include <poll.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/file.h>
#include <sys/inotify.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

enum { WIDTH = 1280, HEIGHT = 720, FRAME_SIZE = WIDTH * HEIGHT * 2 };

static void die(const char *message)
{
    perror(message);
    exit(1);
}

static long long now_ms(void)
{
    struct timespec time;
    if (clock_gettime(CLOCK_MONOTONIC, &time) != 0)
        die("clock_gettime");
    return (long long)time.tv_sec * 1000 + time.tv_nsec / 1000000;
}

static int numeric(const char *name)
{
    if (!*name)
        return 0;
    for (; *name; name++) {
        if (!isdigit((unsigned char)*name))
            return 0;
    }
    return 1;
}

/* fstatat follows bind mounts, so sandboxed apps are counted too. */
static int has_client(dev_t device)
{
    DIR *processes = opendir("/proc");
    if (!processes)
        die("opendir /proc");
    int found = 0;
    struct dirent *process;
    while (!found && (process = readdir(processes))) {
        if (!numeric(process->d_name) || atoi(process->d_name) == getpid())
            continue;
        char path[512];
        snprintf(path, sizeof(path), "/proc/%s", process->d_name);
        struct stat owner;
        if (stat(path, &owner) != 0 || owner.st_uid != getuid())
            continue;
        snprintf(path, sizeof(path), "/proc/%s/fd", process->d_name);
        DIR *descriptors = opendir(path);
        if (!descriptors)
            continue;
        struct dirent *descriptor;
        while ((descriptor = readdir(descriptors))) {
            if (!numeric(descriptor->d_name))
                continue;
            struct stat target;
            if (fstatat(dirfd(descriptors), descriptor->d_name, &target, 0) == 0 &&
                S_ISCHR(target.st_mode) && target.st_rdev == device) {
                found = 1;
                break;
            }
        }
        closedir(descriptors);
    }
    closedir(processes);
    return found;
}

static pid_t start_capture(int *output, int rear)
{
    int stream[2];
    if (pipe2(stream, O_CLOEXEC) != 0)
        die("pipe2");
    pid_t child = fork();
    if (child < 0)
        die("fork");
    if (child == 0) {
        close(stream[0]);
        if (dup2(stream[1], STDOUT_FILENO) < 0)
            _exit(127);
        close(stream[1]);
        if (rear)
            execl("/usr/bin/gst-launch-1.0", "gst-launch-1.0", "-q",
                  "libcamerasrc", "camera-name=\\\\_SB_.PCI0.I2C3.CAMR",
                  "!", "video/x-raw,width=1280,height=720,framerate=30/1",
                  "!", "videoconvert", "!", "video/x-raw,format=YUY2",
                  "!", "fdsink", "fd=1", "sync=false", (char *)NULL);
        else
            execl("/usr/bin/gst-launch-1.0", "gst-launch-1.0", "-q",
                  "libcamerasrc", "camera-name=\\\\_SB_.PCI0.I2C2.CAMF", "!", "video/x-raw,width=1280,height=720,framerate=30/1",
                  "!", "videoconvert", "!", "video/x-raw,format=RGBA",
                  "!", "frei0r-filter-hqdn3d", "!", "videoconvert", "!", "video/x-raw,format=YUY2",
                  "!", "fdsink", "fd=1", "sync=false", (char *)NULL);
        _exit(127);
    }
    close(stream[1]);
    *output = stream[0];
    fprintf(stderr, "camera capture started (pid %ld)\n", (long)child);
    return child;
}

static void stop_capture(pid_t child, int output)
{
    close(output);
    kill(child, SIGTERM);
    while (waitpid(child, NULL, 0) < 0 && errno == EINTR) {}
    fprintf(stderr, "camera capture stopped\n");
}

int main(int argc, char **argv)
{
    const char *device = argc > 1 ? argv[1] : "/dev/video90";
    int rear = argc > 2 && strcmp(argv[2], "rear") == 0;
    const char *runtime = getenv("XDG_RUNTIME_DIR");
    if (!runtime)
        die("XDG_RUNTIME_DIR");
    char lock_path[512];
    snprintf(lock_path, sizeof(lock_path), "%s/surface-camera-hardware.lock", runtime);
    int lock_fd = open(lock_path, O_CREAT | O_RDWR | O_CLOEXEC, 0600);
    if (lock_fd < 0)
        die("open camera lock");
    struct stat node;
    if (stat(device, &node) != 0 || !S_ISCHR(node.st_mode))
        die("stat camera device");
    int camera_fd = open(device, O_WRONLY | O_CLOEXEC);
    if (camera_fd < 0)
        die("open v4l2loopback");

    struct v4l2_format format = { .type = V4L2_BUF_TYPE_VIDEO_OUTPUT };
    if (ioctl(camera_fd, VIDIOC_G_FMT, &format) != 0)
        die("VIDIOC_G_FMT");
    format.fmt.pix.width = WIDTH;
    format.fmt.pix.height = HEIGHT;
    format.fmt.pix.pixelformat = V4L2_PIX_FMT_YUYV;
    format.fmt.pix.sizeimage = FRAME_SIZE;
    if (ioctl(camera_fd, VIDIOC_S_FMT, &format) != 0)
        die("VIDIOC_S_FMT");

    unsigned char frame[FRAME_SIZE];
    for (size_t i = 0; i < sizeof(frame); i += 4) {
        frame[i] = frame[i + 2] = 16;
        frame[i + 1] = frame[i + 3] = 128;
    }
    if (write(camera_fd, frame, sizeof(frame)) != sizeof(frame))
        die("initial frame");

    int events = inotify_init1(IN_NONBLOCK | IN_CLOEXEC);
    if (events < 0 || inotify_add_watch(events, device,
                                      IN_OPEN | IN_CLOSE_WRITE | IN_CLOSE_NOWRITE) < 0)
        die("inotify camera device");

    pid_t child = 0;
    int output = -1;
    size_t received = 0;
    long long last_client = 0;
    long long last_frame = 0;
    long long last_scan = 0;
    int client = 0;
    for (;;) {
        struct pollfd ready[2] = {
            { .fd = events, .events = POLLIN },
            { .fd = output, .events = POLLIN },
        };
        int result = poll(ready, child ? 2 : 1, 1000);
        if (result < 0 && errno != EINTR)
            die("poll");
        if (ready[0].revents & POLLIN) {
            char buffer[4096];
            while (read(events, buffer, sizeof(buffer)) > 0) {}
            last_scan = 0;
        }

        long long current = now_ms();
        if (current - last_scan >= 1000) {
            client = has_client(node.st_rdev);
            last_scan = current;
            if (client)
                last_client = current;
        }
        if (client && !child) {
            if (flock(lock_fd, LOCK_EX | LOCK_NB) == 0) {
                child = start_capture(&output, rear);
                received = 0;
                last_frame = current;
            } else if (errno != EWOULDBLOCK) {
                die("flock camera");
            }
        } else if (child && !client && current - last_client >= 2000) {
            stop_capture(child, output);
            child = 0;
            output = -1;
            if (flock(lock_fd, LOCK_UN) != 0)
                die("unlock camera");
        }

        if (child && current - last_frame >= 6000) {
            stop_capture(child, output);
            fprintf(stderr, "no camera frames within six seconds; stopping\n");
            return 1;
        }

        if (child && ready[1].fd == output && ready[1].revents) {
            ssize_t count = read(output, frame + received, sizeof(frame) - received);
            if (count <= 0) {
                stop_capture(child, output);
                fprintf(stderr, "camera stream failed; stopping to avoid repeated sensor starts\n");
                return 1;
            }
            received += (size_t)count;
            if (received == sizeof(frame)) {
                if (write(camera_fd, frame, sizeof(frame)) != sizeof(frame))
                    die("camera frame");
                received = 0;
                last_frame = now_ms();
            }
        }
    }
}
