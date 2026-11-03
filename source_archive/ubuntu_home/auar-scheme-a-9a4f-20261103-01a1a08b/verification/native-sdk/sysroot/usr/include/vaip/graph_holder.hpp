/*
 * Copyright 2019 Xilinx Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
#pragma once
#include "./_sanity_check.hpp"
#include "./my_ort.hpp"
#include <memory>
#include <string>
#include <vector>
namespace xir {
class Graph;
class Subgraph;
} // namespace xir
namespace vaip_core {

class GraphHolder {
public:
  explicit GraphHolder(const std::string& filename);
  explicit GraphHolder(std::unique_ptr<const xir::Graph> graph);
  explicit GraphHolder(std::unique_ptr<const xir::Graph> graph,
                       xir::Subgraph* subgraph);
  ~GraphHolder() = default;

public:
  VAIP_DLL_SPEC const xir::Graph* get_graph() const;
  VAIP_DLL_SPEC std::vector<const xir::Subgraph*> get_subgraphs() const;
  const xir::Graph* release() { return graph_.release(); }

private:
  void init_subgraph();

private:
  std::unique_ptr<const xir::Graph> graph_;
  std::vector<const xir::Subgraph*> subgraphs_;
};

} // namespace vaip_core
