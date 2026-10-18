#pragma once
#include <array>
#include <cstddef>
#include <vector>

namespace reliable_focus {
// Interleaved, row-major normalized RGB float64. No implicit clipping or scaling.
struct Image {
    std::size_t height = 0, width = 0, channels = 3;
    std::vector<double> pixels;
};
struct CrossfitResult {
    std::array<double, 2> sigmas{{0.0, 0.0}};
    std::size_t eligible_blocks = 0;
    std::size_t selected_blocks_per_source_per_fold = 0;
    bool available = false;
    double valid_pixel_fraction = 0.0;
    // Empty if unavailable, otherwise source A then B, fold 0 then 1.
    std::vector<std::array<double, 2>> fold_variances;
};
// Throws std::invalid_argument for malformed, non-finite or out-of-range input.
CrossfitResult estimate_crossfit(const Image& a, const Image& b);
}  // namespace reliable_focus
