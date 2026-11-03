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
#include "./my_ort.hpp"
namespace vaip_core {
VAIP_DLL_SPEC const std::string& node_get_output_name(const Node& node);
VAIP_DLL_SPEC bool node_is_op(const Node& node, const std::string& op_type,
                              const std::string& domain);
VAIP_DLL_SPEC int node_get_output_element_type(const Node& node);
} // namespace vaip_core
