import ctypes as C
import math
import os
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parent
LIB=C.CDLL(str(ROOT/os.environ.get('AURA_TRAJECTORY_HOST_LIB','libaura_trajectory_host.so')))
STEP=LIB.aura_trajectory_step
STEP.restype=C.c_int
STEP.argtypes=[C.c_double,C.POINTER(C.c_double),C.c_double,C.c_double,C.c_double,C.c_double,C.POINTER(C.c_double)]
PVA=C.c_double*3


def step(current,target,dt=.02,vmax=60.,amax=120.,jmax=600.):
    output=PVA(-999.,-998.,-997.)
    result=STEP(dt,PVA(*current),target,vmax,amax,jmax,output)
    return result,list(output)


class TrajectoryTests(unittest.TestCase):
    def check_step(self,current,target,dt=.02):
        result,output=step(current,target,dt)
        self.assertEqual(result,0,(current,target,dt,result))
        self.assertLessEqual(abs(output[1]),60.+1e-7)
        self.assertLessEqual(abs(output[2]),120.+1e-7)
        self.assertLessEqual(abs(output[2]-current[2]),600.*dt+1e-7)
        return output

    def test_start_matches_analytic_jerk_segment(self):
        output=self.check_step([1500.,0.,0.],30.)
        self.assertAlmostEqual(output[0],1500.+600.*.02**3/6,places=10)
        self.assertAlmostEqual(output[1],600.*.02**2/2,places=10)
        self.assertAlmostEqual(output[2],12.,places=10)

    def test_command_acceleration_survives_each_new_call(self):
        state=self.check_step([1500.,0.,0.],30.)
        second=self.check_step(state,30.)
        self.assertAlmostEqual(second[2],24.,places=10)
        self.assertAlmostEqual(second[1],.48,places=10)

    def test_reaches_and_holds_target_velocity(self):
        state=[1500.,0.,0.]
        for _ in range(100):state=self.check_step(state,30.)
        self.assertAlmostEqual(state[1],30.,places=8)
        self.assertAlmostEqual(state[2],0.,places=8)

    def test_reversal_and_stop_keep_acceleration_continuous(self):
        state=[1500.,0.,0.]
        for target in ([30.]*80+[-30.]*120+[0.]*100):
            state=self.check_step(state,target)
        self.assertAlmostEqual(state[1],0.,places=8)
        self.assertAlmostEqual(state[2],0.,places=8)

    def test_actual_dt_is_used_without_resetting_command_state(self):
        state=[1500.,0.,0.]
        for i in range(300):state=self.check_step(state,20.*math.sin(i*.07),(.005,.02,.08,.015,.03)[i%5])

    def test_rapid_retargets_preserve_limits(self):
        state=[1500.,0.,0.]
        for i in range(1000):state=self.check_step(state,55.*math.sin(i*.19))

    def test_invalid_inputs_leave_output_unchanged(self):
        cases=[([1500.,0.,0.],61.,.02,60.,120.,600.),
               ([1500.,61.,0.],0.,.02,60.,120.,600.),
               ([1500.,60.,20.],0.,.02,60.,120.,600.),
               ([1500.,0.,121.],0.,.02,60.,120.,600.),
               ([float('nan'),0.,0.],0.,.02,60.,120.,600.)]
        for dt in (0.,-.1,.100001,float('nan'),float('inf')):
            cases.append(([1500.,0.,0.],0.,dt,60.,120.,600.))
        for current,target,dt,vmax,amax,jmax in cases:
            result,output=step(current,target,dt,vmax,amax,jmax)
            self.assertNotEqual(result,0)
            self.assertEqual(output,[-999.,-998.,-997.])

    def test_null_pointers_are_rejected(self):
        self.assertNotEqual(STEP(.02,None,0.,60.,120.,600.,PVA()),0)
        self.assertNotEqual(STEP(.02,PVA(1500.,0.,0.),0.,60.,120.,600.,None),0)

    def test_input_output_may_alias(self):
        state=PVA(1500.,0.,0.)
        self.assertEqual(STEP(.02,state,30.,60.,120.,600.,state),0)
        self.assertAlmostEqual(state[2],12.,places=10)

    def test_outer_position_and_source_contract_is_explicitly_required(self):
        result,output=step([1601.,1.,0.],1.)
        self.assertEqual(result,0)
        self.assertAlmostEqual(output[0],1601.02)


if __name__=='__main__':unittest.main()
