#ifndef AURA_TRAJECTORY_H
#define AURA_TRAJECTORY_H
#ifdef __cplusplus
extern "C" {
#endif
/* p/v/a in us, us/s, us/s^2; dt in seconds, 0<dt<=0.1.
 * Return 0 on success, errno-style error otherwise; output unchanged on error.
 * This is trajectory math only: no source authorization, position limit or IO.
 */
int aura_trajectory_step(double dt,const double current_pva[3],double target_velocity,
                         double max_velocity,double max_acceleration,double max_jerk,
                         double output_pva[3]);
#ifdef __cplusplus
}
#endif
#endif
