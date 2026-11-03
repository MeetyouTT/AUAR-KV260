#include "facial_envelope.hpp"
#include <cassert>
#include <cmath>
#include <iostream>
int main(){
 aura_yuki::FacialEnvelope e;
 assert(e.closed_weight()==0.f);
 for(int i=0;i<9;++i){const auto a=e.closed_weight();e.step(true);assert(e.closed_weight()>=a);assert(e.closed_weight()-a<.11112f);}
 assert(e.closed_weight()==1.f);
 for(int i=0;i<9;++i)e.step(false);
 assert(e.closed_weight()==0.f);
 for(int i=0;i<4;++i)e.step(true);
 auto before=e.closed_weight();e.step(false);
 assert(e.closed_weight()<before && e.closed_weight()>0.f);
 for(int i=0;i<1000000;++i){e.step((i/13)%2);assert(std::isfinite(e.closed_weight())&&e.closed_weight()>=0.f&&e.closed_weight()<=1.f);}
 std::cout<<"PASS: bounded 150ms closure/reopening, reversal and long state churn\n";
}
