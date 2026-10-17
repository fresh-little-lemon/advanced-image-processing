#include "multifocus/fusion.hpp"
#include <opencv2/imgproc.hpp>
#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <vector>

namespace multifocus {
namespace {
void validate(const cv::Mat& a, const cv::Mat& b) {
    if (a.empty() || b.empty() || a.dims != 2 || b.dims != 2 ||
        a.type() != CV_64FC3 || b.type() != CV_64FC3 || a.size() != b.size())
        throw std::invalid_argument("Expected equal-size nonempty CV_64FC3 RGB images");
    for (const auto* image : {&a, &b})
        for (int y = 0; y < image->rows; ++y)
            for (int x = 0; x < image->cols; ++x)
                for (double value : image->at<cv::Vec3d>(y,x).val)
                    if (!std::isfinite(value) || value < 0 || value > 1)
                        throw std::invalid_argument("RGB samples must be finite and in [0,1]");
}
cv::Mat gray(const cv::Mat& rgb) {
    std::vector<cv::Mat> channels;
    cv::split(rgb, channels);
    return channels[0]*0.299 + channels[1]*0.587 + channels[2]*0.114;
}
cv::Mat mean(const cv::Mat& input, int size) {
    cv::Mat result;
    cv::boxFilter(input, result, CV_64F, cv::Size(size,size), cv::Point(-1,-1), true, cv::BORDER_REFLECT);
    return result;
}
cv::Mat focus(const cv::Mat& input, bool sml) {
    cv::Mat response;
    if (sml) {
        const cv::Mat horizontal = (cv::Mat_<double>(1,3) << 1, -2, 1);
        cv::Mat dx, dy;
        cv::filter2D(input, dx, CV_64F, horizontal, cv::Point(-1,-1), 0, cv::BORDER_REFLECT);
        cv::filter2D(input, dy, CV_64F, horizontal.t(), cv::Point(-1,-1), 0, cv::BORDER_REFLECT);
        response = cv::abs(dx) + cv::abs(dy);
    } else {
        const cv::Mat kernel = (cv::Mat_<double>(3,3) << 0,1,0,1,-4,1,0,1,0);
        cv::filter2D(input, response, CV_64F, kernel, cv::Point(-1,-1), 0, cv::BORDER_REFLECT);
        response = cv::abs(response);
    }
    return mean(response, 7);
}
// A binary median is a majority vote. Explicit reflection avoids medianBlur's
// replicate-only border and its lack of CV_64F support for kernel size seven.
cv::Mat median_binary7(const cv::Mat& mask) {
    cv::Mat result(mask.size(), CV_64F);
    for (int y=0; y<mask.rows; ++y) for (int x=0; x<mask.cols; ++x) {
        int count=0;
        for (int dy=-3; dy<=3; ++dy) for (int dx=-3; dx<=3; ++dx) {
            int yy=cv::borderInterpolate(y+dy,mask.rows,cv::BORDER_REFLECT);
            int xx=cv::borderInterpolate(x+dx,mask.cols,cv::BORDER_REFLECT);
            count += mask.at<double>(yy,xx) > 0.5;
        }
        result.at<double>(y,x) = count >= 25 ? 1.0 : 0.0;
    }
    return result;
}
cv::Mat guided(const cv::Mat& guide, const cv::Mat& mask) {
    const cv::Mat mean_i=mean(guide,11), mean_p=mean(mask,11);
    const cv::Mat covariance=mean(guide.mul(mask),11)-mean_i.mul(mean_p);
    cv::Mat variance=mean(guide.mul(guide),11)-mean_i.mul(mean_i);
    cv::max(variance,0.0,variance);
    cv::Mat alpha;
    cv::divide(covariance,variance+1e-3,alpha);
    const cv::Mat beta=mean_p-alpha.mul(mean_i);
    cv::Mat result=mean(alpha,11).mul(guide)+mean(beta,11);
    cv::max(result,0.0,result);
    cv::min(result,1.0,result);
    return result;
}
}
cv::Mat fuse(const cv::Mat& a, const cv::Mat& b, const std::string& method) {
    validate(a,b);
    if (method=="average") return (a+b)*0.5;
    if (method!="laplacian" && method!="sml" && method!="guided")
        throw std::invalid_argument("Method must be average, laplacian, sml, or guided");
    const cv::Mat ga=gray(a), gb=gray(b);
    const cv::Mat sa=focus(ga,method=="sml"), sb=focus(gb,method=="sml");
    cv::Mat binary, weight;
    cv::compare(sa,sb,binary,cv::CMP_GE);
    binary.convertTo(weight,CV_64F,1.0/255.0);
    if (method=="guided") weight=guided((ga+gb)*0.5,median_binary7(weight));
    cv::Mat result(a.size(),CV_64FC3);
    for (int y=0;y<a.rows;++y) for (int x=0;x<a.cols;++x) {
        const double w=weight.at<double>(y,x);
        result.at<cv::Vec3d>(y,x)=a.at<cv::Vec3d>(y,x)*w+b.at<cv::Vec3d>(y,x)*(1-w);
    }
    return result;
}
}
