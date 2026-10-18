#include "crossfit.hpp"
#include <algorithm>
#include <cmath>
#include <limits>
#include <numeric>
#include <stdexcept>
#include <utility>

namespace reliable_focus {
namespace {
constexpr double kMadNormal = 0.6744897501960817;
void validate(const Image& image) {
    if (image.channels != 3 || image.height < 12 || image.width < 12)
        throw std::invalid_argument("require RGB inputs of size at least 12");
    const auto limit = std::numeric_limits<std::size_t>::max();
    if (image.width > limit / image.height || image.width * image.height > limit / 3)
        throw std::invalid_argument("image dimensions overflow");
    if (image.pixels.size() != image.height * image.width * 3)
        throw std::invalid_argument("RGB storage does not match dimensions");
    for (double value : image.pixels)
        if (!std::isfinite(value) || value < 0.0 || value > 1.0)
            throw std::invalid_argument("input values must be finite and in [0,1]");
}
double median(std::vector<double> values) {
    const auto half = values.size() / 2;
    std::nth_element(values.begin(), values.begin() + half, values.end());
    const double upper = values[half];
    return values.size() % 2 ? upper :
        (upper + *std::max_element(values.begin(), values.begin() + half)) / 2.0;
}
double mad(const std::vector<double>& values) {
    const double center = median(values);
    std::vector<double> deviations; deviations.reserve(values.size());
    for (double v : values) deviations.push_back(std::abs(v - center));
    return median(std::move(deviations));
}
double mad_variance(const std::vector<double>& values) {
    const double sigma = mad(values) / (2.0 * kMadNormal);
    return sigma * sigma;
}
std::vector<double> grayscale(const Image& image) {
    std::vector<double> result(image.height * image.width);
    for (std::size_t p = 0; p < result.size(); ++p)
        result[p] = image.pixels[3*p] * 0.299 + image.pixels[3*p+1] * 0.587 +
                    image.pixels[3*p+2] * 0.114;
    return result;
}
// Validity erosion implementation is specified and verified against the Python
// reference in tests/parity.py; no clipping or sensor-mask inference is applied.
std::vector<unsigned char> valid_support(const Image& a, const Image& b) {
    const std::size_t h = a.height, w = a.width;
    std::vector<std::size_t> invalid_prefix((h + 1) * (w + 1), 0);
    for (std::size_t r = 0; r < h; ++r) {
        std::size_t row = 0;
        for (std::size_t c = 0; c < w; ++c) {
            bool good = true;
            for (std::size_t ch = 0; ch < 3; ++ch) {
                const auto i = (r*w+c)*3+ch;
                good = good && a.pixels[i] > 0.0 && a.pixels[i] < 1.0 &&
                               b.pixels[i] > 0.0 && b.pixels[i] < 1.0;
            }
            row += !good;
            invalid_prefix[(r+1)*(w+1)+c+1] = invalid_prefix[r*(w+1)+c+1] + row;
        }
    }
    std::vector<unsigned char> valid(h*w, 0);
    for (std::size_t r = 4; r + 4 < h; ++r)
        for (std::size_t c = 4; c + 4 < w; ++c) {
            const auto y0=r-4, y1=r+5, x0=c-4, x1=c+5;
            const auto invalid = invalid_prefix[y1*(w+1)+x1] + invalid_prefix[y0*(w+1)+x0]
                               -invalid_prefix[y0*(w+1)+x1] - invalid_prefix[y1*(w+1)+x0];
            valid[r*w+c] = invalid == 0;
        }
    return valid;
}
}  // namespace
CrossfitResult estimate_crossfit(const Image& a, const Image& b) {
    validate(a); validate(b);
    if (a.height != b.height || a.width != b.width)
        throw std::invalid_argument("require matching RGB shapes");
    const auto h = a.height, w = a.width;
    const auto valid = valid_support(a,b);
    CrossfitResult out;
    out.valid_pixel_fraction = static_cast<double>(std::count(valid.begin(),valid.end(),1)) /
                               static_cast<double>(valid.size());
    std::vector<std::pair<std::size_t,std::size_t>> positions;
    for (std::size_t i=2; i<h-9; i+=8)
        for (std::size_t j=2; j<w-9; j+=8) {
            bool good=true;
            for (std::size_t u=0; u<8 && good; ++u)
                for (std::size_t v=0; v<8; ++v)
                    if (!valid[(i+u)*w+j+v]) { good=false; break; }
            if (good) positions.emplace_back(i,j);
        }
    out.eligible_blocks=positions.size();
    const auto k=std::max<std::size_t>(1,static_cast<std::size_t>(std::ceil(0.2*positions.size())));
    out.selected_blocks_per_source_per_fold=positions.empty()?0:k;
    out.available=!positions.empty() && k>=2;
    if (!out.available) return out;
    for (const auto* image : {&a,&b}) {
        const auto y=grayscale(*image);
        std::vector<std::array<double,16>> blocks; blocks.reserve(positions.size());
        for (const auto& position : positions) {
            std::array<double,16> block{};
            for (std::size_t u=0; u<4; ++u)
                for (std::size_t v=0; v<4; ++v) {
                    const auto r=position.first+2*u, c=position.second+2*v;
                    block[4*u+v]=y[(r+1)*w+c+1]-y[r*w+c+1]-y[(r+1)*w+c]+y[r*w+c];
                }
            blocks.push_back(block);
        }
        std::array<double,2> folds{};
        for (std::size_t fold=0; fold<2; ++fold) {
            std::vector<double> scores; scores.reserve(blocks.size());
            for (const auto& block : blocks) {
                std::vector<double> train; train.reserve(8);
                for (std::size_t u=0; u<4; ++u)
                    for (std::size_t v=0; v<4; ++v)
                        if ((u+v)%2==fold) train.push_back(block[4*u+v]);
                scores.push_back(mad(train));
            }
            std::vector<std::size_t> ids(blocks.size()); std::iota(ids.begin(),ids.end(),0);
            std::stable_sort(ids.begin(),ids.end(),[&](auto i,auto j){return scores[i]<scores[j];});
            std::vector<double> test; test.reserve(k*8);
            for (std::size_t n=0; n<k; ++n)
                for (std::size_t u=0; u<4; ++u)
                    for (std::size_t v=0; v<4; ++v)
                        if ((u+v)%2!=fold) test.push_back(blocks[ids[n]][4*u+v]);
            folds[fold]=mad_variance(test);
        }
        out.fold_variances.push_back(folds);
        out.sigmas[out.fold_variances.size()-1]=std::sqrt((folds[0]+folds[1])/2.0);
    }
    return out;
}
}  // namespace reliable_focus
