/**
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
#include <string>

#include "xir/graph/graph.hpp"
#include "xir/graph/graph_template.hpp"
#include "xir/graph/subgraph.hpp"

namespace xcompiler {

class PluginHelper {
 public:
  static xir::Subgraph* filter_by_name(xir::Graph* graph,
                                       const std::string& name);

  static std::set<xir::Subgraph*> filter_by_type(xir::Graph* graph,
                                                 const std::string& type);

  static std::set<xir::Subgraph*> filter_by_template(xir::Graph* graph,
                                                     xir::GraphTemplate* temp);

  static std::set<xir::Subgraph*> filter(
      xir::Graph* graph,
      std::function<std::set<xir::Subgraph*>(std::set<xir::Subgraph*>)> func);

  static std::set<xir::Subgraph*> merge_subgraph(
      std::set<xir::Subgraph*> subgraph_list);
};

class Plugin {
 public:
  virtual std::string get_plugin_name() = 0;

  virtual bool if_pre_process() { return true; };

  virtual std::string get_device() = 0;

  virtual std::map<std::string, std::string> get_runner() = 0;

  virtual std::set<xir::Subgraph*> partition(xir::Graph* graph) = 0;

  virtual void compile(xir::Subgraph* subgraph) = 0;
};

}  // namespace xcompiler
