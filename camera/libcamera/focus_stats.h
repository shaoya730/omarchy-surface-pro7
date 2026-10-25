/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once
#include <cstdint>

namespace libcamera {

struct FocusStats {
    uint64_t energy = 0;
    uint64_t norm = 0;
    uint64_t sum = 0;
    uint64_t samples = 0;

    FocusStats &operator+=(const FocusStats &other)
    {
        energy += other.energy;
        norm += other.norm;
        sum += other.sum;
        samples += other.samples;
        return *this;
    }
};

/* Same-colour horizontal curvature, limited to the central half of a row.
 * Input is unpacked 10-bit Bayer; odd columns on this row are green.
 */
inline FocusStats raw10FocusLine(const uint16_t *row, unsigned int width)
{
    FocusStats result;
    for (unsigned int x = 3; x + 2 < width; x += 4) {
        if (x < width / 4 || x >= width * 3 / 4)
            continue;
        int c = row[x], left = row[x - 2], right = row[x + 2];
        if (c < 16 || c > 1008 || left < 16 || left > 1008 || right < 16 || right > 1008)
            continue;
        int laplacian = left - 2 * c + right;
        result.energy += uint64_t(laplacian * laplacian);
        result.norm += uint64_t(c * c);
        result.sum += c;
        result.samples++;
    }
    return result;
}

} /* namespace libcamera */
