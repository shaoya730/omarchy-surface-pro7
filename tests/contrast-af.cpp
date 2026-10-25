// SPDX-License-Identifier: LGPL-2.1-or-later
#include "../camera/libcamera/contrast_af.h"

#include <cassert>
#include <cmath>
#include <limits>
#include <deque>

using libcamera::ipa::soft::ContrastAf;

static double score(int position, int target, unsigned int frame)
{
    double distance = position - target;
    double noise = 1.0 + 0.025 * std::sin(frame);
    return (0.001 + 0.05 * std::exp(-distance * distance / (2 * 45.0 * 45.0))) * noise;
}

static void convergence(int low, int high, int target)
{
    ContrastAf af;
    assert(af.configure(low, high));
    af.trigger(0);
    int position = low;
    unsigned int moves = 0;
    for (unsigned int frame = 0; frame < 1000; frame += 4) {
        if (auto next = af.process(frame, score(position, target, frame))) {
            assert(*next >= low && *next <= high);
            position = *next;
            moves++;
        }
    }
    assert(af.state() == ContrastAf::State::Focused);
    assert(std::abs(position - target) <= 16);
    assert(moves > 3 && moves < 60);
    af.cancel();
    for (unsigned int frame = 1000; frame < 1200; frame += 4)
        assert(!af.process(frame, score(position, low, frame)));
    assert(af.state() == ContrastAf::State::Idle);
}

int main()
{
    ContrastAf future;
    assert(future.configure(0, 1023));
    future.trigger(100);
    assert(!future.process(96, 0.1));
    assert(future.state() == ContrastAf::State::Scanning);
    convergence(0, 1023, 256);
    convergence(120, 600, 136);
    convergence(0, 1023, 960);
    ContrastAf af;
    assert(!af.configure(0, 0));
    assert(!af.configure(600, 120));
    assert(!af.process(0, 0.1));
    assert(af.configure(0, 1023));
    af.trigger(0);
    for (unsigned int frame = 0; frame < 1000; frame += 4)
        af.process(frame, 0.001);
    assert(af.state() == ContrastAf::State::Failed);
    for (unsigned int frame = 1000; frame < 1300; frame += 4)
        assert(!af.process(frame, 0.001));
    af.trigger(1300);
    for (unsigned int frame = 1300; frame < 2400; frame += 4)
        assert(!af.process(frame, std::numeric_limits<double>::quiet_NaN()));
    assert(af.state() == ContrastAf::State::Failed);
    assert(af.configure(0, 1023));
    af.setContinuous(true);
    af.trigger(0);
    int position = 0;
    for (unsigned int frame = 0; frame < 2400; frame += 4) {
        int target = frame < 1000 ? 256 : 448;
        if (auto next = af.process(frame, score(position, target, frame)))
            position = *next;
    }
    assert(af.state() == ContrastAf::State::Focused);
    assert(std::abs(position - 448) <= 16);
    af.fail();
    for (unsigned int frame = 2400; frame < 3500; frame += 4)
        assert(!af.process(frame, score(position, 256, frame)));
    assert(af.state() == ContrastAf::State::Failed);
    assert(af.configure(0, 1023));
    af.trigger(0);
    std::deque<std::pair<unsigned int,int>> delayed;
    position = 0;
    for (unsigned int frame = 0; frame < 1000; frame += 4) {
        while (!delayed.empty() && delayed.front().first <= frame) {
            position = delayed.front().second;
            delayed.pop_front();
        }
        if (auto next = af.process(frame, score(position, 256, frame)))
            delayed.emplace_back(frame + 8, *next);
    }
    assert(af.state() == ContrastAf::State::Focused);
    assert(std::abs(position - 256) <= 16);
    assert(af.configure(0, 1023));
    af.setContinuous(true);
    af.trigger(0);
    position = 0;
    for (unsigned int frame = 0; frame < 2400; frame += 4) {
        double value = frame < 1000 ? 0.001 : score(position, 256, frame);
        if (auto next = af.process(frame, value, frame < 1000 ? 0.001 : 0.1)) position = *next;
    }
    assert(af.state() == ContrastAf::State::Focused);
    assert(std::abs(position - 256) <= 16);
}
