/*
 *  Copyright 2022 Xilinx Inc.
 *
 *  Licensed under the Apache License, Version 2.0 (the "License");
 *  you may not use this file except in compliance with the License.
 *  You may obtain a copy of the License at
 *
 *  http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 **/
#pragma once
/// basically there are 3 types client if VAIP.
///
/// 1. ORT VITISAI Execution Provider.
///     USE_VITISAI is defined.
/// 2. VAIP pass
/// 3. Vaip Custom OP
///
/// different user see different part of vaip.
#define VAIP_USER__ORT_VITIS_AI_EP 1
#define VAIP_USER__PASS 2
#define VAIP_USER__CUSTOM_OP 3
#define VAIP_USER__INTERNAL 4

#ifndef VAIP_USER
#  if defined(USE_VITISAI)
#    define VAIP_USER VAIP_USER__ORT_VITIS_AI_EP
#  elif defined(VAIP_CUSTOM_OP)
#    define VAIP_USER VAIP_USER__CUSTOM_OP
#  else
#    define VAIP_USER VAIP_USER__PASS
#  endif
#endif

#if VAIP_USER == VAIP_USER__PASS
#  include "./graph.hpp"
#  include "./node_arg.hpp"
#  include "./pass.hpp"
#  include "./rewrite_rule.hpp"
#  include "./util.hpp"
#endif

#include "./vaip_ort_api.hpp"

#if VAIP_USER == VAIP_USER__ORT_VITIS_AI_EP
#  include "./vaip_ort.hpp"
#endif

#if VAIP_USER == VAIP_USER__CUSTOM_OP
#  include "./anchor_point.hpp"
#  include "./pass_context.pb.h"
#endif

#if VAIP_USER == VAIP_USER__CUSTOM_OP || VAIP_USER == VAIP_USER__ORT_VITIS_AI_EP
#  include "./custom_op.hpp"
#endif

#if VAIP_USER == VAIP_USER__CUSTOM_OP || VAIP_USER == VAIP_USER__PASS
#  include "./transpose.hpp"
#endif
