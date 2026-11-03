#include "aura_trajectory.h"
#include <ruckig/ruckig.hpp>
#include <cerrno>
#include <cmath>
#include <new>

namespace {
constexpr double tolerance=1e-8;
bool feasible(double velocity,double acceleration,double vmax,double amax,double jmax) {
    if(!std::isfinite(velocity) || !std::isfinite(acceleration)
            || std::abs(velocity)>vmax+tolerance || std::abs(acceleration)>amax+tolerance)return false;
    // Velocity mode does not itself validate max_velocity. Exclude initial
    // states that must exceed it even under immediate maximum-jerk braking.
    const double peak=velocity+std::copysign(acceleration*acceleration/(2*jmax),acceleration);
    return std::isfinite(peak) && std::abs(peak)<=vmax+tolerance;
}
}

extern "C" __attribute__((visibility("default")))
int aura_trajectory_step(double dt,const double current_pva[3],double target_velocity,
                         double max_velocity,double max_acceleration,double max_jerk,
                         double output_pva[3]) {
    if(!current_pva || !output_pva || !std::isfinite(dt) || dt<=0 || dt>.1
            || !std::isfinite(target_velocity) || !std::isfinite(max_velocity) || max_velocity<=0
            || !std::isfinite(max_acceleration) || max_acceleration<=0
            || !std::isfinite(max_jerk) || max_jerk<=0
            || !std::isfinite(current_pva[0]) || std::abs(target_velocity)>max_velocity
            || !feasible(current_pva[1],current_pva[2],max_velocity,max_acceleration,max_jerk))return EINVAL;
    try {
        ruckig::Ruckig<1> generator(dt);
        ruckig::InputParameter<1> input;
        ruckig::OutputParameter<1> output;
        input.control_interface=ruckig::ControlInterface::Velocity;
        input.current_position={current_pva[0]};
        input.current_velocity={current_pva[1]};
        input.current_acceleration={current_pva[2]};
        input.target_velocity={target_velocity};
        input.target_acceleration={0.};
        input.max_velocity={max_velocity};
        input.max_acceleration={max_acceleration};
        input.max_jerk={max_jerk};
        if(!generator.validate_input<false>(input,true,true))return EINVAL;
        const auto result=generator.update(input,output);
        if(result!=ruckig::Result::Working && result!=ruckig::Result::Finished)return EDOM;
        const double p=output.new_position[0],v=output.new_velocity[0],a=output.new_acceleration[0];
        if(!std::isfinite(p) || !feasible(v,a,max_velocity,max_acceleration,max_jerk)
                || std::abs(a-current_pva[2])>max_jerk*dt+tolerance)return ERANGE;
        output_pva[0]=p;output_pva[1]=v;output_pva[2]=a;
        return 0;
    } catch(const std::bad_alloc&) {return ENOMEM;}
      catch(...) {return EDOM;}
}
