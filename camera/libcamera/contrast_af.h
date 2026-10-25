/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>
#include <optional>

namespace libcamera::ipa::soft {

/* Frame numbers belong to one streaming session. Scores are exposure-normalized. */
class ContrastAf
{
public:
    enum class State { Idle, Scanning, Focused, Failed };

    bool configure(int minimum, int maximum)
    {
        *this = ContrastAf();
        enabled_ = minimum >= 0 && maximum > minimum && maximum <= 65535;
        minimum_ = minimum;
        maximum_ = maximum;
        position_ = minimum;
        return enabled_;
    }

    void setContinuous(bool enabled) { continuous_ = enabled; }
    State state() const { return state_; }

    void cancel()
    {
        state_ = State::Idle;
        pending_ = false;
        lowCount_ = 0;
    }

    void fail()
    {
        state_ = State::Failed;
        pending_ = false;
        continuous_ = false;
    }

    void trigger(uint32_t frame)
    {
        if (!enabled_)
            return;
        state_ = State::Scanning;
        phase_ = Phase::Coarse;
        started_ = frame;
        notBefore_ = frame + 32; /* Let exposure and the capture queue settle. */
        next_ = minimum_;
        pending_ = true;
        best_ = minimum_;
        bestScore_ = 0;
        lowestScore_ = std::numeric_limits<double>::max();
        samples_ = 0;
        sum_ = 0;
        lowCount_ = 0;
    }

    std::optional<int> process(uint32_t frame, double score, double sceneContrast = 0)
    {
        if (!enabled_ || state_ == State::Idle)
            return {};
        if (state_ == State::Scanning && int32_t(frame - started_) < 0)
            return {};
        if (state_ == State::Scanning && frame - started_ > 900) {
            state_ = State::Failed;
            pending_ = false;
            completed_ = frame;
            referenceScene_ = lastScene_;
            return {};
        }
        if (!std::isfinite(score) || score < 0)
            return {};
        if (std::isfinite(sceneContrast) && sceneContrast >= 0)
            lastScene_ = sceneContrast;
        if (state_ != State::Scanning) {
            bool sceneChanged = lastScene_ > std::max(referenceScene_, 0.0001) * 2 ||
                                (referenceScene_ > 0.0001 && lastScene_ < referenceScene_ * 0.5);
            if (continuous_ && frame - completed_ > 300) {
                bool changed = state_ == State::Focused
                             ? score < reference_ * 0.65 || sceneChanged
                             : sceneChanged;
                lowCount_ = changed ? lowCount_ + 1 : 0;
                if (lowCount_ >= 6)
                    trigger(frame);
            }
            if (state_ != State::Scanning)
                return {};
        }
        if (int32_t(frame - notBefore_) < 0)
            return {};
        if (pending_) {
            position_ = std::clamp(next_, minimum_, maximum_);
            pending_ = false;
            notBefore_ = frame + 8; /* Discard in-flight frames after a lens move. */
            samples_ = 0;
            sum_ = 0;
            return position_;
        }
        sum_ += score;
        if (++samples_ < 2)
            return {};
        score = sum_ / samples_;
        samples_ = 0;
        sum_ = 0;
        if (phase_ == Phase::Return) {
            reference_ = score;
            referenceScene_ = lastScene_;
            completed_ = frame;
            state_ = bestScore_ > 1e-6 && lowestScore_ < bestScore_ * 0.75 && score >= bestScore_ * 0.8
                   ? State::Focused : State::Failed;
            return {};
        }
        lowestScore_ = std::min(lowestScore_, score);
        if (score > bestScore_) {
            bestScore_ = score;
            best_ = position_;
        }
        if (phase_ == Phase::Coarse) {
            if (position_ < maximum_) {
                next_ = std::min(position_ + 64, maximum_);
            } else {
                phase_ = Phase::Fine;
                fineEnd_ = std::min(best_ + 64, maximum_);
                next_ = std::max(best_ - 64, minimum_);
            }
        } else if (position_ < fineEnd_) {
            next_ = std::min(position_ + 16, fineEnd_);
        } else {
            phase_ = Phase::Return;
            next_ = best_;
        }
        pending_ = true;
        return {};
    }

private:
    enum class Phase { Coarse, Fine, Return };
    State state_ = State::Idle;
    Phase phase_ = Phase::Coarse;
    bool enabled_ = false, continuous_ = false, pending_ = false;
    int minimum_ = 0, maximum_ = 0, position_ = 0, next_ = 0, best_ = 0, fineEnd_ = 0;
    uint32_t started_ = 0, completed_ = 0, notBefore_ = 0;
    unsigned int samples_ = 0, lowCount_ = 0;
    double bestScore_ = 0, lowestScore_ = 0, reference_ = 0, sum_ = 0;
    double referenceScene_ = 0, lastScene_ = 0;
};

} /* namespace libcamera::ipa::soft */
