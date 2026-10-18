#include "crossfit.hpp"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <random>
#include <vector>
int main(){
    constexpr int warmups=5,repeats=30;
    std::mt19937_64 rng(20261018);std::normal_distribution<double>noise(0.,5./255.);
    volatile double sink=0.;
    std::cout<<std::setprecision(17)<<"{\"scope\":\"crossfit estimator only; two RGB inputs; validation, allocations and estimation included; generation and I/O excluded\",\"warmups\":"<<warmups<<",\"repeats\":"<<repeats<<",\"threads\":1,\"seed\":20261018,\"cases\":[";
    int index=0;
    for(const auto& dims: {std::pair<int,int>{480,640},{720,1280},{1080,1920}}){
        reliable_focus::Image a{static_cast<std::size_t>(dims.first),static_cast<std::size_t>(dims.second),3,std::vector<double>(static_cast<std::size_t>(dims.first)*dims.second*3)},b=a;
        for(auto&v:a.pixels)v=std::clamp(.45+noise(rng),0.,1.);
        for(auto&v:b.pixels)v=std::clamp(.45+noise(rng),0.,1.);
        for(int n=0;n<warmups;++n){const auto r=reliable_focus::estimate_crossfit(a,b);sink+=r.sigmas[0];}
        std::vector<double>ms; reliable_focus::CrossfitResult last;
        for(int n=0;n<repeats;++n){const auto start=std::chrono::steady_clock::now();last=reliable_focus::estimate_crossfit(a,b);const auto stop=std::chrono::steady_clock::now();sink+=last.sigmas[1];ms.push_back(std::chrono::duration<double,std::milli>(stop-start).count());}
        auto ordered=ms;std::sort(ordered.begin(),ordered.end());double mean=std::accumulate(ms.begin(),ms.end(),0.)/ms.size(),var=0.;for(auto x:ms)var+=(x-mean)*(x-mean);var/=ms.size();
        if(index++)std::cout<<",";
        std::cout<<"{\"height\":"<<dims.first<<",\"width\":"<<dims.second<<",\"median_ms\":"<<(ordered[14]+ordered[15])/2<<",\"mean_ms\":"<<mean<<",\"min_ms\":"<<ordered.front()<<",\"max_ms\":"<<ordered.back()<<",\"p95_nearest_rank_ms\":"<<ordered[28]<<",\"stddev_population_ms\":"<<std::sqrt(var)<<",\"eligible_blocks\":"<<last.eligible_blocks<<",\"samples_ms\":[";
        for(std::size_t n=0;n<ms.size();++n){if(n)std::cout<<",";std::cout<<ms[n];}std::cout<<"]}";
    }
    std::cout<<"],\"checksum\":"<<sink<<"}\n";
}
