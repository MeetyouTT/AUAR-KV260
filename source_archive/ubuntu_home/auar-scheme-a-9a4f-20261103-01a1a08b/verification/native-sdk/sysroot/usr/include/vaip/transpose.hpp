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
#include "./_sanity_check.hpp"
#include "./export.hpp"
#include <cstdlib>
#include <vector>
namespace vaip_core {
VAIP_DLL_SPEC
void transpose_f(const float* src, float* dst,
                 const std::vector<int64_t>& shape,
                 const std::vector<int64_t>& perm);
VAIP_DLL_SPEC
void transpose_i8(const int8_t* src, int8_t* dst,
                  const std::vector<int64_t>& shape,
                  const std::vector<int64_t>& perm);

} // namespace vaip_core
