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
#include "./custom_op.hpp"
#include "./export.hpp"
#include "./vaip_ort_api.hpp"
/// header file used by ort VITISAI execution providers.
namespace vaip_core {
VAIP_DLL_SPEC void set_the_global_api(OrtApiForVaip* api);
VAIP_DLL_SPEC std::vector<std::unique_ptr<ExecutionProvider>>
compile_onnx_model_3(const std::string& model_path, const Graph& graph, const char* json_config);
} // namespace vaip_core
