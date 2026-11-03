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
#include <sstream>
namespace vaip_core {
void dump_graph(const Graph& graph, const std::string& filename);
template <typename T> std::string container_as_string(const T& container) {
  std::ostringstream str;
  str << "[";
  int c = 0;
  for (auto& v : container) {
    if (c != 0) {
      str << ",";
    }
    str << v;
    c = c + 1;
  }
  str << "]";
  return str.str();
}

VAIP_DLL_SPEC std::string convert_to_xir_op_type(const std::string& domain,
                                                 const std::string& op_type);

std::string find_file_in_path(const std::string& file, const char* env_name,
                              bool required);
std::string slurp(const char* filename);

VAIP_DLL_SPEC TensorProtoPtr tensor_proto_new_floats(
    const std::string& name, const std::vector<int64_t>& shape,
    const std::vector<float>& data);
VAIP_DLL_SPEC TensorProtoPtr
tensor_proto_new_i32(const std::string& name, const std::vector<int64_t>& shape,
                     const std::vector<int32_t>& data);
VAIP_DLL_SPEC TensorProtoPtr
tensor_proto_new_i8(const std::string& name, const std::vector<int64_t>& shape,
                    const std::vector<int8_t>& data);

VAIP_DLL_SPEC NodeAttributesPtr node_clone_attributes(const Node& node);

VAIP_DLL_SPEC int scale_to_fix_point(float scale);

} // namespace vaip_core
