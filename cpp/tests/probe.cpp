// Float64 transport for cross-language tests; deliberately separate from image CLI.
#include "multifocus/fusion.hpp"
#include <iomanip>
#include <iostream>
#include <stdexcept>
int main(int argc,char** argv) {
    try {
        int height=0,width=0;
        if(argc!=2 || !(std::cin>>height>>width) || height<1 || width<1 ||
           static_cast<long long>(height)*width>10000000)
            throw std::invalid_argument("Expected method argument and H W RGB samples on stdin");
        cv::Mat a(height,width,CV_64FC3),b(height,width,CV_64FC3);
        for(auto* image:{&a,&b}) for(int y=0;y<height;++y) for(int x=0;x<width;++x)
            for(double& value:image->at<cv::Vec3d>(y,x).val)
                if(!(std::cin>>value)) throw std::invalid_argument("Missing input samples");
        const cv::Mat result=multifocus::fuse(a,b,argv[1]);
        std::cout<<std::setprecision(17);
        for(int y=0;y<height;++y) for(int x=0;x<width;++x)
            for(double value:result.at<cv::Vec3d>(y,x).val) std::cout<<value<<'\n';
    } catch(const std::exception& error) {
        std::cerr<<error.what()<<'\n'; return 1;
    }
}
