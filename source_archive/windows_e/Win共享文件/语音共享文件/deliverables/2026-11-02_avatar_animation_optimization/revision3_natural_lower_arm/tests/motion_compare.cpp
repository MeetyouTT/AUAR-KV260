#define SecondaryMotion PreviousSecondaryMotion
#define bind_arm_swing previous_bind_arm_swing
#include "../baseline/native/secondary_motion.hpp"
#undef SecondaryMotion
#undef bind_arm_swing
#include "../candidate/native/secondary_motion.hpp"
#include <iostream>
#include <limits>
#include <stdexcept>

int main(){
 try{
  aura_yuki::PreviousSecondaryMotion old;
  aura_yuki::SecondaryMotion revised;
  std::array<float,6> old_previous{},new_previous{};
  double old_min=1e9,old_max=-1e9,new_min=1e9,new_max=-1e9,old_speed=0.,new_speed=0.;
  std::uint64_t unchanged=0;
  for(int i=0;i<60000;++i){
   const int mood=(i/211)%3;
   auto a=old.step(mood),b=revised.step(mood);
   for(int k=0;k<6;++k)if(k!=4){if(a[k]!=b[k])throw std::runtime_error("Unrequested motion channel changed");++unchanged;}
   if(!std::isfinite(b[4])||std::abs(b[4])>4.000001)throw std::runtime_error("Lower arm out of bounds");
   old_speed=std::max(old_speed,60.*std::abs(a[4]-old_previous[4]));new_speed=std::max(new_speed,60.*std::abs(b[4]-new_previous[4]));
   old_min=std::min(old_min,double(a[4]));old_max=std::max(old_max,double(a[4]));new_min=std::min(new_min,double(b[4]));new_max=std::max(new_max,double(b[4]));
   old_previous=a;new_previous=b;
  }
  const double ratio=(new_max-new_min)/(old_max-old_min);
  if(ratio>.45||ratio<.2||new_speed>6.0001||new_speed>old_speed*.55)throw std::runtime_error("Requested lower-arm reduction not achieved");
  std::cout<<"{\"status\":\"PASS\",\"author_ticks\":60000,\"unchanged_other_channel_values\":"<<unchanged
   <<",\"old_lower_min\":"<<old_min<<",\"old_lower_max\":"<<old_max<<",\"new_lower_min\":"<<new_min<<",\"new_lower_max\":"<<new_max
   <<",\"range_ratio\":"<<ratio<<",\"old_peak_speed_deg_s\":"<<old_speed<<",\"new_peak_speed_deg_s\":"<<new_speed<<",\"device_or_GPU_used\":false}"<<std::endl;
 }catch(const std::exception& e){std::cerr<<e.what()<<std::endl;return 1;}
}
