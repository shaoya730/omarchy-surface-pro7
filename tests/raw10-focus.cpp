// SPDX-License-Identifier: LGPL-2.1-or-later
#include "../camera/libcamera/focus_stats.h"
#include <array>
#include <cassert>
#include <cmath>

int main()
{
    std::array<uint16_t, 256> line;
    for (unsigned int i = 0; i < line.size(); i++)
        line[i] = i % 2 ? 500 : 200;
    auto flat = libcamera::raw10FocusLine(line.data(), line.size());
    assert(flat.samples > 0 && flat.energy == 0);
    for (unsigned int i = 1; i < line.size(); i += 2)
        line[i] = 450 + int(40 * std::sin(i * 0.3));
    auto sharp = libcamera::raw10FocusLine(line.data(), line.size());
    assert(sharp.energy > 0 && sharp.norm > 0);
    for (auto &value : line) value *= 2;
    auto brighter = libcamera::raw10FocusLine(line.data(), line.size());
    double a = double(sharp.energy) / sharp.norm;
    double b = double(brighter.energy) / brighter.norm;
    // Non-clipped exposure scaling should leave the normalized metric unchanged.
    assert(std::abs(a - b) < 1e-12);
    for (unsigned int width = 0; width < 12; width++)
        libcamera::raw10FocusLine(line.data(), width);
    line.fill(1023);
    assert(libcamera::raw10FocusLine(line.data(), line.size()).samples == 0);
}
