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
#include "./anchor_point.hpp"
#include "./my_ort.hpp"
#include "./node_attr.hpp"
#include "gsl/gsl-lite.hpp"
#include <cassert>
#include <functional>
namespace vaip_core {

VAIP_DLL_SPEC ModelPtr model_load(const std::string& filename);
VAIP_DLL_SPEC ModelPtr model_clone(const Model& model);
#ifndef VAIP_USE_DEPRECATED_API
[[deprecated("This API will be removed in the future release version. Please "
             "use NodeBuilder instread.")]]
#endif
VAIP_DLL_SPEC Node&
graph_add_node(Graph& graph, const std::string& name,
               const std::string& op_type, const std::string& description,
               const std::vector<const NodeArg*>& input_args,
               const std::vector<const NodeArg*>& output_args,
               NodeAttributesPtr attributes, const std::string& domain);

VAIP_DLL_SPEC std::vector<const NodeArg*>
node_inputs_2_node_args(const std::vector<NodeInput>& inputs);
struct NodeBuilder {
public:
  VAIP_DLL_SPEC explicit NodeBuilder(Graph& graph);
  VAIP_DLL_SPEC const Node& build();
  VAIP_DLL_SPEC NodeBuilder& clone_node(const Node& node);
  VAIP_DLL_SPEC NodeBuilder& clone_op_type(const Node& node);
  VAIP_DLL_SPEC NodeBuilder&
  set_op_type(const std::string& op_type,
              const std::string& domain = "com.xilinx");

  VAIP_DLL_SPEC NodeBuilder& clone_inputs(const Node& node);
  VAIP_DLL_SPEC NodeBuilder&
  set_input_nodes(const std::vector<const Node*>& input_nodes);
  VAIP_DLL_SPEC NodeBuilder&
  set_input_node_args(const std::vector<const NodeArg*>& input_args);
  VAIP_DLL_SPEC NodeBuilder& append_input(const Node& node);

  VAIP_DLL_SPEC NodeBuilder& clone_attrs(const Node& node);
  VAIP_DLL_SPEC NodeAttributesBuilder& get_attrs_builder();
  VAIP_DLL_SPEC NodeBuilder& clone_shape(const Node& node);
  VAIP_DLL_SPEC NodeBuilder& set_shape(const gsl::span<const int64_t>& shape);
  VAIP_DLL_SPEC NodeBuilder& clone_shape(const NodeArg& node_arg);
  VAIP_DLL_SPEC NodeBuilder& clone_data_type(const Node& node);
  VAIP_DLL_SPEC NodeBuilder& clone_data_type(const NodeArg& node);
  VAIP_DLL_SPEC NodeBuilder& set_data_type(const std::string& data_type);

  VAIP_DLL_SPEC NodeBuilder& set_anchor_point1(const Node& node);
  VAIP_DLL_SPEC NodeBuilder&
  set_anchor_point2(const Node& node,
                    const AnchorPoint::Description& description);
  VAIP_DLL_SPEC NodeBuilder&
  set_anchor_point3(const Node& node,
                    const AnchorPoint::Description& description,
                    const std::vector<int64_t>& shape);
  VAIP_DLL_SPEC NodeBuilder& set_anchor_point4(
      const Node& node, const AnchorPoint::Description& description,
      const std::vector<int64_t>& shape, const std::string& data_type);

  template <typename T> NodeBuilder& add(const std::string& name, T&& value) {
    if (name == "data_type" || name == "shape") {
      assert(false &&
             "data_type and shape are deprecated, please use set_anchor_point, "
             "clone_shape, set_shape, clone_data_type, set_data_type instead");
    }
    attrs_builder_.add(name, std::forward<T>(value));
    return *this;
  }

private:
  VAIP_DLL_SPEC NodeBuilder& replace_node(const Node& node);
  NodeBuilder& clone_output(const Node& node,
                            const AnchorPoint::Description& description,
                            const std::vector<int64_t>& shape,
                            const std::string& data_type);

private:
  Graph& graph_;
  std::string name_;
  std::string op_type_;
  std::string description_;
  std::vector<const NodeArg*> input_args_;
  std::vector<const NodeArg*> output_args_;
  NodeAttributesPtr attrs_;
  NodeAttributesBuilder attrs_builder_;
  std::string domain_;
  std::vector<int64_t> shape_;
  std::string data_type_;
  std::unique_ptr<AnchorPoint> anchor_point_ = nullptr;
  const Node* anchor_node_ = nullptr;
};
VAIP_DLL_SPEC std::vector<const Node*>
graph_get_output_nodes(const Graph& graph);

VAIP_DLL_SPEC std::vector<const Node*>
graph_get_output_nodes(const Graph& graph);
// garbage collection by removing dangling nodes.
VAIP_DLL_SPEC void graph_gc(Graph& graph);

} // namespace vaip_core
