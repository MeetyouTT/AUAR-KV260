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
#include "./graph_holder.hpp"
#include "./vaip_plugin.hpp"

struct OrtApi;
typedef struct OrtApi OrtApi;
typedef struct OrtKernelContext OrtKernelContext;

namespace vaip_core {
class CustomOp;
class ExecutionProvider
    : public WithPlugin<ExecutionProvider, const onnxruntime::Graph*,
                        std::shared_ptr<vaip_core::GraphHolder>,
                        const xir::Subgraph*> {
public:
  static constexpr char entry_point[] = "create_execution_provider";

public:
  VAIP_DLL_SPEC ExecutionProvider(std::shared_ptr<GraphHolder> graph,
                                  const xir::Subgraph* subgraph);
  VAIP_DLL_SPEC virtual ~ExecutionProvider();

public:
  virtual std::vector<std::string> get_meta_def_inputs() const = 0;
  virtual std::vector<std::string> get_meta_def_outputs() const = 0;
  virtual std::vector<std::string>
  get_meta_def_constant_initializer() const = 0;
  virtual std::unique_ptr<CustomOp> compile() const = 0;

private:
  std::shared_ptr<vaip_core::GraphHolder> graph_;
  const xir::Subgraph* subgraph_;
};

class CustomOp {

public:
  VAIP_DLL_SPEC CustomOp(std::shared_ptr<GraphHolder> graph,
                         const xir::Subgraph* subgraph);
  VAIP_DLL_SPEC virtual ~CustomOp();

public:
  virtual void Compute(const OrtApi* api, OrtKernelContext* context) const = 0;

private:
  std::shared_ptr<vaip_core::GraphHolder> graph_;
  const xir::Subgraph* subgraph_;
};

} // namespace vaip_core
