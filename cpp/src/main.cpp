#include "multifocus/fusion.hpp"
#include <opencv2/imgcodecs.hpp>
#include <opencv2/imgproc.hpp>
#include <iostream>
#include <stdexcept>

static cv::Mat read_rgb(const std::string& path) {
    cv::Mat image=cv::imread(path,cv::IMREAD_UNCHANGED);
    if (image.empty() || image.type()!=CV_8UC3)
        throw std::invalid_argument("CLI requires an 8-bit three-channel image: "+path);
    cv::cvtColor(image,image,cv::COLOR_BGR2RGB);
    image.convertTo(image,CV_64FC3,1.0/255.0);
    return image;
}
int main(int argc,char** argv) {
    cv::setNumThreads(1);
    if (argc!=5) {
        std::cerr<<"Usage: multifocus_cli inputA inputB output.png average|laplacian|sml|guided\n";
        return 2;
    }
    try {
        const std::string path=argv[3];
        if (path.size()<4 || path.substr(path.size()-4)!=".png")
            throw std::invalid_argument("Output must have the .png extension");
        cv::Mat result=multifocus::fuse(read_rgb(argv[1]),read_rgb(argv[2]),argv[4]);
        result.convertTo(result,CV_8UC3,255.0);
        cv::cvtColor(result,result,cv::COLOR_RGB2BGR);
        if (!cv::imwrite(path,result)) throw std::runtime_error("Could not write output");
    } catch (const std::exception& error) {
        std::cerr<<error.what()<<'\n';
        return 1;
    }
    return 0;
}
