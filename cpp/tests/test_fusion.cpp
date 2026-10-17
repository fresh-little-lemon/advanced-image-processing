#include "multifocus/fusion.hpp"
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>
static void check(bool ok,const char* message) { if(!ok) throw std::runtime_error(message); }
int main() {
    try {
        for(const cv::Size size:{cv::Size(1,1),cv::Size(2,3),cv::Size(23,19)}) {
            const cv::Mat a(size,CV_64FC3,cv::Scalar(0,0,0));
            const cv::Mat b(size,CV_64FC3,cv::Scalar(1,1,1));
            check(cv::norm(multifocus::fuse(a,b,"average"),cv::Mat(size,CV_64FC3,cv::Scalar(.5,.5,.5)),cv::NORM_INF)<1e-14,"Average failed");
            for(const std::string method:{"laplacian","sml","guided"})
                check(cv::norm(multifocus::fuse(a,b,method),a,cv::NORM_INF)<1e-12,"Constant tie must select A");
            cv::Mat random(size,CV_64FC3); cv::RNG rng(42); rng.fill(random,cv::RNG::UNIFORM,0.,1.);
            for(const std::string method:{"average","laplacian","sml","guided"})
                check(cv::norm(multifocus::fuse(random,random,method),random,cv::NORM_INF)<1e-12,"Identical input changed");
        }
        const cv::Mat valid(4,4,CV_64FC3,cv::Scalar(.3,.4,.5));
        for(int kind=0;kind<4;++kind) {
            cv::Mat invalid=valid.clone();
            if(kind==0) invalid.at<cv::Vec3d>(0,0)[0]=std::numeric_limits<double>::quiet_NaN();
            if(kind==1) invalid.at<cv::Vec3d>(0,0)[0]=1.01;
            if(kind==2) invalid=cv::Mat(4,4,CV_32FC3);
            if(kind==3) invalid=cv::Mat(2,2,CV_64FC3);
            bool rejected=false;
            try { multifocus::fuse(valid,invalid,"average"); } catch(const std::invalid_argument&) { rejected=true; }
            check(rejected,"Invalid input accepted");
        }
        bool rejected=false;
        try { multifocus::fuse(valid,valid,"unknown"); } catch(const std::invalid_argument&) { rejected=true; }
        check(rejected,"Unknown method accepted");
        std::cout<<"C++ fusion invariants passed\n";
    } catch(const std::exception& error) { std::cerr<<error.what()<<'\n';return 1; }
}
