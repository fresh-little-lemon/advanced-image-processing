#include "multifocus/fusion.hpp"
#include <opencv2/imgcodecs.hpp>
#include <opencv2/imgproc.hpp>
#include <algorithm>
#include <chrono>
#include <iostream>
#include <stdexcept>
#include <vector>
#if defined(__linux__)
#include <sys/resource.h>
#endif
static cv::Mat read(const char* path) {
    cv::Mat x=cv::imread(path,cv::IMREAD_COLOR);
    if(x.empty()) throw std::runtime_error("Could not read benchmark input");
    cv::cvtColor(x,x,cv::COLOR_BGR2RGB); x.convertTo(x,CV_64FC3,1./255.); return x;
}
int main(int argc,char** argv) {
    if(argc!=4) return 2;
    try {
        cv::setNumThreads(1);
        const cv::Mat a=read(argv[1]),b=read(argv[2]);
        cv::Mat result;
        for(int i=0;i<3;++i) result=multifocus::fuse(a,b,argv[3]);
        std::vector<double> times;
        for(int i=0;i<10;++i) {
            const auto start=std::chrono::steady_clock::now();
            result=multifocus::fuse(a,b,argv[3]);
            times.push_back(std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count());
        }
        std::cout<<"{\"height\":"<<a.rows<<",\"width\":"<<a.cols<<",\"opencv\":\""<<CV_VERSION
                 <<"\",\"threads\":"<<cv::getNumThreads()<<",\"warmups\":3,\"repeats\":10,\"core_ms\":[";
        for(size_t i=0;i<times.size();++i) std::cout<<(i?",":"")<<times[i];
        std::cout<<"],\"output_mean\":"<<cv::mean(result)[0];
#if defined(__linux__)
        rusage usage{}; getrusage(RUSAGE_SELF,&usage);
        std::cout<<",\"process_peak_rss_kib\":"<<usage.ru_maxrss;
#endif
        std::cout<<"}\n";
    } catch(const std::exception& error) { std::cerr<<error.what()<<'\n';return 1; }
}
