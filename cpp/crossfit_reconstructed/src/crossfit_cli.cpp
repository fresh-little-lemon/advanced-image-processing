#include "crossfit.hpp"
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>

// Test transport: CFITF64\0, little-endian uint64 H/W, A then B RGB doubles.
// This is a bounded test protocol, not a general image decoder.
int main(int argc,char** argv) {
    try {
        if(argc!=2) throw std::invalid_argument("usage: crossfit_cli fixture.bin");
        std::ifstream in(argv[1],std::ios::binary);
        char magic[8]{}; std::uint64_t h=0,w=0;
        in.read(magic,8); in.read(reinterpret_cast<char*>(&h),8); in.read(reinterpret_cast<char*>(&w),8);
        if(!in || std::string(magic,8)!=std::string("CFITF64\0",8))
            throw std::invalid_argument("invalid fixture header");
        std::uint16_t endian=1;
        if(*reinterpret_cast<unsigned char*>(&endian)!=1)
            throw std::invalid_argument("fixture transport requires little-endian host");
        if(h<12 || w<12 || h>100000 || w>100000 || h>20000000/w)
            throw std::invalid_argument("invalid or excessive fixture dimensions");
        const auto count=static_cast<std::size_t>(h*w*3);
        reliable_focus::Image a{static_cast<std::size_t>(h),static_cast<std::size_t>(w),3,std::vector<double>(count)}, b=a;
        in.read(reinterpret_cast<char*>(a.pixels.data()),count*sizeof(double));
        in.read(reinterpret_cast<char*>(b.pixels.data()),count*sizeof(double));
        if(!in || in.peek()!=std::char_traits<char>::eof())
            throw std::invalid_argument("truncated or trailing fixture bytes");
        const auto r=reliable_focus::estimate_crossfit(a,b);
        std::cout<<std::setprecision(17)<<"{\"sigmas\":["<<r.sigmas[0]<<","<<r.sigmas[1]
                 <<"],\"eligible_blocks\":"<<r.eligible_blocks
                 <<",\"selected_blocks_per_source_per_fold\":"<<r.selected_blocks_per_source_per_fold
                 <<",\"available\":"<<(r.available?"true":"false")
                 <<",\"valid_pixel_fraction\":"<<r.valid_pixel_fraction<<",\"fold_variances\":[";
        for(std::size_t i=0;i<r.fold_variances.size();++i) {
            if(i) std::cout<<",";
            std::cout<<"["<<r.fold_variances[i][0]<<","<<r.fold_variances[i][1]<<"]";
        }
        std::cout<<"]}\n"; return 0;
    } catch(const std::exception& e) { std::cerr<<e.what()<<"\n"; return 2; }
}
