#include "crossfit.hpp"
#include <cmath>
#include <functional>
#include <iostream>
#include <limits>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>
using reliable_focus::Image;
using reliable_focus::estimate_crossfit;
Image filled(std::size_t h=48,std::size_t w=48,double v=.4) { return {h,w,3,std::vector<double>(h*w*3,v)}; }
void require(bool value,const std::string& message) {if(!value)throw std::runtime_error(message);}
void rejects(const Image& a,const Image& b) {bool caught=false;try{estimate_crossfit(a,b);}catch(const std::invalid_argument&){caught=true;} require(caught,"expected invalid_argument");}
int main() {
    std::vector<std::pair<std::string,std::function<void()>>> tests;
    auto add=[&](std::string name,std::function<void()> fn){tests.emplace_back(name,fn);};
    add("constant_zero_sigma",[]{auto x=filled();auto r=estimate_crossfit(x,x);require(r.available&&r.sigmas[0]==0&&r.sigmas[1]==0,"constant");});
    add("support_border_zero",[]{auto x=filled();auto r=estimate_crossfit(x,x);require(r.valid_pixel_fraction==1600./2304&&r.eligible_blocks==16&&r.selected_blocks_per_source_per_fold==4,"support");});
    add("zero_saturated",[]{auto r=estimate_crossfit(filled(48,48,0),filled());require(!r.available&&r.valid_pixel_fraction==0&&r.fold_variances.empty(),"saturation");});
    add("one_saturated",[]{auto r=estimate_crossfit(filled(),filled(48,48,1));require(!r.available&&r.sigmas[1]==0,"saturation");});
    add("minimum_size_fallback",[]{auto r=estimate_crossfit(filled(12,12),filled(12,12));require(!r.available&&r.eligible_blocks==0,"min size");});
    add("one_selected_fallback",[]{auto r=estimate_crossfit(filled(26,26),filled(26,26));require(!r.available&&r.eligible_blocks==1&&r.selected_blocks_per_source_per_fold==1,"one selected");});
    add("mismatched_height",[]{rejects(filled(),filled(49,48));});
    add("mismatched_width",[]{rejects(filled(),filled(48,49));});
    add("too_small_height",[]{rejects(filled(11,48),filled(11,48));});
    add("too_small_width",[]{rejects(filled(48,11),filled(48,11));});
    add("zero_dimensions",[]{rejects(Image{},Image{});});
    add("wrong_channels",[]{auto x=filled();x.channels=4;rejects(x,x);});
    add("short_storage",[]{auto x=filled();x.pixels.pop_back();rejects(x,x);});
    add("long_storage",[]{auto x=filled();x.pixels.push_back(.4);rejects(x,x);});
    add("nan_rejected",[]{auto x=filled();x.pixels[10]=std::numeric_limits<double>::quiet_NaN();rejects(x,filled());});
    add("positive_infinity_rejected",[]{auto x=filled();x.pixels[10]=std::numeric_limits<double>::infinity();rejects(filled(),x);});
    add("negative_infinity_rejected",[]{auto x=filled();x.pixels[10]=-std::numeric_limits<double>::infinity();rejects(x,filled());});
    add("negative_rejected",[]{auto x=filled();x.pixels[10]=-.001;rejects(x,filled());});
    add("greater_than_one_rejected",[]{auto x=filled();x.pixels[10]=1.001;rejects(filled(),x);});
    add("dimension_overflow_rejected",[]{Image x; x.height=std::numeric_limits<std::size_t>::max();x.width=12;rejects(x,x);});
    add("channel_product_overflow_rejected",[]{Image x;x.height=std::numeric_limits<std::size_t>::max()/12;x.width=12;rejects(x,x);});
    add("source_swap",[]{auto a=filled(64,80),b=a;std::mt19937 rng(18);std::uniform_real_distribution<double>d(.2,.8);for(auto&x:a.pixels)x=d(rng);for(auto&x:b.pixels)x=d(rng);auto x=estimate_crossfit(a,b),y=estimate_crossfit(b,a);require(x.sigmas[0]==y.sigmas[1]&&x.sigmas[1]==y.sigmas[0]&&x.fold_variances[0]==y.fold_variances[1],"swap");});
    add("affine_scale",[]{auto a=filled(64,80),b=a;std::mt19937 rng(19);std::uniform_real_distribution<double>d(.2,.8);for(auto&x:a.pixels)x=d(rng);for(auto&x:b.pixels)x=d(rng);auto before=estimate_crossfit(a,b);for(auto&x:a.pixels)x=.5*x+.2;for(auto&x:b.pixels)x=.5*x+.2;auto after=estimate_crossfit(a,b);require(std::abs(after.sigmas[0]-.5*before.sigmas[0])<1e-14&&std::abs(after.sigmas[1]-.5*before.sigmas[1])<1e-14,"affine");});
    add("immutable_inputs",[]{auto a=filled(),b=a,aa=a,bb=b;estimate_crossfit(a,b);require(a.pixels==aa.pixels&&b.pixels==bb.pixels,"input mutation");});
    add("disjoint_stencils",[]{int masks[64]{};for(int u=0;u<4;++u)for(int v=0;v<4;++v)for(int y=0;y<2;++y)for(int x=0;x<2;++x){auto& m=masks[(2*u+y)*8+2*v+x];require(m==0,"overlap");m=1+(u+v)%2;}int counts[3]{};for(int m:masks)++counts[m];require(counts[1]==32&&counts[2]==32,"coverage");});
    std::cout<<"{\"suite\":\"native_cpp17\",\"tests\":[";int failed=0;
    for(std::size_t i=0;i<tests.size();++i){bool passed=true;try{tests[i].second();}catch(const std::exception&e){passed=false;++failed;std::cerr<<tests[i].first<<": "<<e.what()<<"\n";}if(i)std::cout<<",";std::cout<<"{\"name\":\""<<tests[i].first<<"\",\"passed\":"<<(passed?"true":"false")<<"}";}
    std::cout<<"],\"total\":"<<tests.size()<<",\"failed\":"<<failed<<"}\n";return failed?1:0;
}
