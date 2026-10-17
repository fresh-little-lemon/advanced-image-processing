#pragma once
#include <opencv2/core.hpp>
#include <string>

namespace multifocus {
// Inputs: nonempty, equal-size CV_64FC3 RGB images, finite and in [0,1].
// No gamma decoding is applied. All filters use half-sample symmetric reflection.
// Returns an owning CV_64FC3 image in [0,1]. Tied focus scores select A.
cv::Mat fuse(const cv::Mat& a, const cv::Mat& b, const std::string& method);
}
