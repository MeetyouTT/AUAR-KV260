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
#include <cassert>
#include <functional>
#include <gsl/gsl-lite.hpp>
#include <vector>
namespace vaip_core {
struct OrtApiForVaip {
  // model
  Model* (*model_load)(const std::string& file);
  void (*model_delete)(Model* model);
  Model* (*model_clone)(const Model& model);
  Graph& (*model_main_graph)(Model& model);
  // graph
  const std::string& (*graph_get_name)(const Graph& graph);
  const Model& (*graph_get_model)(const Graph& graph);
  std::vector<const Node*> (*graph_nodes)(const Graph& graph);
  std::vector<const NodeArg*> (*graph_get_inputs)(const Graph& graph);
  std::vector<const NodeArg*> (*graph_get_outputs)(const Graph& graph);
  void (*graph_set_outputs)(Graph& graph,
                            gsl::span<const NodeArg* const> outputs);
  const Node* (*graph_get_node)(const Graph& graph, size_t index);
  const Node* (*graph_producer_node)(const Graph& graph,
                                     const std::string& node_arg_name);
  const NodeArg* (*graph_get_node_arg)(const Graph& graph,
                                       const std::string& name);
  std::vector<size_t> (*graph_get_node_in_topoligical_order)(
      const Graph& graph);
  std::vector<size_t> (*graph_get_node_in_topoligical_order_reverse)(
      const Graph& graph);
  std::string (*graph_as_string)(const Graph& graph);
  const InitializedTensorSet& (*graph_get_all_initialized_tensors)(
      const Graph& graph);
  void (*dump_graph)(const Graph& graph, const std::string& filename);
  void (*graph_remove_node)(Graph& graph, const NodeInput& node_input);
  Node& (*graph_add_node)(Graph& graph, const std::string& name,
                          const std::string& op_type,
                          const std::string& description,
                          const std::vector<const NodeArg*>& input_args,
                          const std::vector<const NodeArg*>& output_args,
                          NodeAttributes& attributes,
                          const std::string& domain);
  void (*graph_save)(const Graph& graph, const std::string& filename,
                     const std::string& dat_filename);
  Node& (*graph_fuse)(Graph& graph, const std::string& name,
                      const std::string& op_type,
                      const std::vector<size_t>& nodes,
                      const std::vector<std::string>& inputs,
                      const std::vector<std::string>& outputs,
                      const std::vector<std::string>& constant_initializers);
  bool (*graph_resolve_needed)(const Graph& graph);
  int (*graph_resolve)(Graph& graph);
  void (*graph_set_graph_resolve_needed)(Graph& graph);
  std::vector<const Node*> (*graph_get_consumer_nodes)(
      const Graph& graph, const std::string& node_arg_name);
  void (*graph_reverse_dfs_from)(
      const Graph& graph, gsl::span<const Node* const> from,
      const std::function<void(const Node*)>& enter,
      const std::function<void(const Node*)>& leave,
      const std::function<bool(const Node* from, const Node* to)>& stop);

  /// node
  //
  const std::string& (*node_get_name)(const Node& node);
  const std::string& (*node_description)(const Node& node);
  size_t (*node_get_index)(const Node& node);
  const std::string& (*node_op_type)(const Node& node);
  const std::string& (*node_op_domain)(const Node& node);
  std::vector<NodeInput> (*node_get_inputs)(const Node& node);
  std::vector<const NodeArg*> (*node_get_input_node_args)(const Node& node);
  std::vector<const NodeArg*> (*node_get_output_node_args)(const Node& node);
  /// return output tensor's name, or node arg's name.
  std::string (*node_get_output_name)(const Node& node);
  /// return the output node arg. Almost all ONNX operators have single output.
  const NodeArg& (*node_get_output_node_arg)(const Node& node);
  std::vector<const AttributeProto*> (*node_get_attributes)(const Node& node);
  NodeAttributes& (*node_get_mutable_attributes)(Node& node);
  /// get output shape
  /// index is usally zero, because most operators only have a single output.
  std::vector<int64_t> (*node_get_output_shape)(const Node& node, int index);
  /// print node as a string for debugging purpose.
  std::string (*node_as_string)(const Node& node);

  bool (*node_has_attr)(const Node& node, const std::string& name);
  std::vector<const NodeArg*> (*node_output_defs)(const Node& node);
  const Graph& (*node_get_function_body)(const Node& node);
  bool (*node_type_is_fused)(const Node& node);

  /// node attrs
  /// int64_t node_get_attr_int(const Node& node, const std::string& name);

  const AttributeProto* (*node_get_attr)(const Node& node,
                                         const std::string& name);
  int64_t (*node_get_attr_int_with_default)(const Node& node,
                                            const std::string& name,
                                            int64_t default_value);
  int64_t (*node_get_attr_int)(const Node& node, const std::string& name);
  float (*node_get_attr_float)(const Node& node, const std::string& name);
  gsl::span<const int64_t> (*node_get_attr_ints)(const Node& node,
                                                 const std::string& name);
  gsl::span<const float> (*node_get_attr_floats)(const Node& node,
                                                 const std::string& name);

  const std::string& (*node_get_attr_string)(const Node& node,
                                             const std::string& name);
  const std::string& (*node_get_attr_string_with_default)(
      const Node& node, const std::string& name,
      const std::string& default_value);

  gsl::span<const std::string* const> (*node_get_attr_strings)(
      const Node& node, const std::string& name);

  std::vector<std::string> (*node_get_attr_strings_with_default)(
      const Node& node, const std::string& name,
      const std::vector<std::string>& default_value);

  const TensorProto& (*node_get_attr_tensor)(const Node& node,
                                             const std::string& name);

  const Node& (*node_input_edges_begin_node)(const Node& node);
  /// node args
  const std::string& (*node_arg_get_name)(const NodeArg& node_arg);
  bool (*node_arg_is_constant)(const Graph& graph, const NodeArg& node_arg);

  std::string (*node_arg_as_string)(const NodeArg& node_arg);

  NodeArg& (*node_arg_clone)(Graph& graph, const NodeArg& node_arg,
                             const std::string& name);
  NodeArg& (*node_arg_new)(Graph& graph, const std::string& name,
                           const std::vector<int64_t>& shape, int element_type);
  std::vector<int64_t> (*node_arg_get_shape_i64)(const NodeArg& node_arg);
  std::vector<std::string> (*node_arg_get_denotation)(const NodeArg& node_arg);
  int64_t (*node_arg_get_dim_by_denotation)(const NodeArg& node_arg,
                                            const std::string& denotation);
  /// here, it is cheating so that even `node_arg` is a const reference,
  /// it still change the shape internally. But we cannot change the
  /// rank, i.e. the size of shape must be same.
  void (*node_arg_set_shape_i64)(const NodeArg& node_arg,
                                 const std::vector<int64_t>& shape);
  void (*node_arg_set_denotation)(const NodeArg& node_arg,
                                  const std::vector<std::string>& denotation);
  int (*node_arg_get_element_type)(const NodeArg& node_arg);
  void (*node_arg_set_element_type)(NodeArg& node_arg,
                                    int /*TensorProto::DataType*/ data_type);
  // void (*node_arg_set_shape)(NodeArg& node_arg, std::vector<int64_t> shape);

  float (*node_arg_get_const_data_as_float)(const Graph& graph,
                                            const NodeArg& node_arg);
  int8_t (*node_arg_get_const_data_as_i8)(const Graph& graph,
                                          const NodeArg& node_arg);
  void (*node_arg_set_scalar_float)(const Graph& graph, const NodeArg& node_arg,
                                    float value);

  gsl::span<const float> (*node_arg_get_const_data_as_floats)(
      const Graph& graph, const NodeArg& node_arg);

  const TensorProto& (*node_arg_get_const_data_as_tensor)(
      const Graph& graph, const NodeArg& node_arg);
  int (*node_arg_get_tensor_shape_size)(const NodeArg& node_arg);
  bool (*node_arg_has_denotation_with_dim)(const NodeArg& node_arg, int dim);
  void (*node_arg_set_denotation_with_dim)(const NodeArg& node_arg, int dim,
                                           const std::string& denotation);

  bool (*node_arg_type_proto_has_denotation)(const NodeArg& node_arg);
  void (*node_arg_type_proto_set_denotation)(NodeArg* node_arg,
                                             const std::string& denotation);

  /// attr proto
  NodeAttributes* (*node_attributes_new)();
  void (*node_attributes_delete)(NodeAttributes* p);
  void (*node_attributes_add)(NodeAttributes& p, AttributeProto&& attr);
  void (*attr_proto_delete)(AttributeProto* attr);
  AttributeProto* (*attr_proto_clone)(const AttributeProto& attr);
  const std::string& (*attr_proto_get_name)(const AttributeProto& attr);
  int (*attr_proto_get_type)(const AttributeProto& attr);
  void (*attr_proto_set_name)(AttributeProto* attr, const std::string& name);
  AttributeProto* (*attr_proto_new_int)(const std::string& name, int64_t value);
  AttributeProto* (*attr_proto_new_float)(const std::string& name, float value);
  AttributeProto* (*attr_proto_new_string)(const std::string& name,
                                           const std::string& value);
  AttributeProto* (*attr_proto_new_tensor)(const std::string& name,
                                           const TensorProto& value);
  AttributeProto* (*attr_proto_new_ints)(const std::string& name,
                                         const std::vector<int64_t>& value);
  AttributeProto* (*attr_proto_new_floats)(const std::string& name,
                                           const std::vector<float>& value);
  AttributeProto* (*attr_proto_new_strings)(
      const std::string& name, const std::vector<std::string>& value);
  int64_t (*attr_proto_get_int)(const AttributeProto& attr);
  float (*attr_proto_get_float)(const AttributeProto& attr);
  const std::string& (*attr_proto_get_string)(const AttributeProto& attr);
  const TensorProto& (*attr_proto_get_tensor)(const AttributeProto& attr);
  gsl::span<const int64_t> (*attr_proto_get_ints)(const AttributeProto& attr);
  gsl::span<const float> (*attr_proto_get_floats)(const AttributeProto& attr);
  std::vector<std::string> (*attr_proto_get_strings)(
      const AttributeProto& attr);
  const std::string (*attr_proto_as_string)(const AttributeProto& attr);

  /// attr_proto makers
  // AttributeProto (*attr_proto_from_i64)(const std::string& name, int64_t);

  ///
  using attr_proto_func_t =
      std::function<AttributeProto(const AttributeProto&)>;

  /// transformer
  // AttributeProto (*attr_proto_transform)(const std::string& function,
  //                                        const AttributeProto& input);
  // tensor_proto
  void (*tensor_proto_delete)(TensorProto* tp);
  std::vector<int64_t> (*tensor_proto_get_shape)(
      const TensorProto& tensor_proto);
  bool (*tensor_proto_is_int64)(const TensorProto& tensor_proto);
  bool (*tensor_proto_is_int8)(const TensorProto& tensor_proto);
  bool (*tensor_proto_is_float)(const TensorProto& tensor_proto);
  int (*tensor_proto_data_type)(const TensorProto& tensor_proto);
  TensorProto* (*tensor_proto_new_floats)(const std::string& name,
                                          const std::vector<int64_t>& shape,
                                          const std::vector<float>& data);
  TensorProto* (*tensor_proto_new_i32)(const std::string& name,
                                       const std::vector<int64_t>& shape,
                                       const std::vector<int32_t>& data);
  TensorProto* (*tensor_proto_new_i8)(const std::string& name,
                                      const std::vector<int64_t>& shape,
                                      const std::vector<int8_t>& data);
  const std::string& (*tensor_proto_get_name)(const TensorProto& tensor_proto);
  size_t (*tensor_proto_raw_data_size)(const TensorProto& tensor);

  float (*tensor_proto_as_float)(const TensorProto& tensor);
  int8_t (*tensor_proto_as_i8)(const TensorProto& tensor);
  int64_t (*tensor_proto_as_i64)(const TensorProto& tensor);
  gsl::span<const int8_t> (*tensor_proto_as_i8s)(const TensorProto& tensor);
  gsl::span<const int64_t> (*tensor_proto_as_i64s)(const TensorProto& tensor);
  gsl::span<const float> (*tensor_proto_as_floats)(const TensorProto& tensor);
  gsl::span<const char> (*tensor_proto_as_raw)(const TensorProto& tensor);

  std::string& (*tensor_proto_get_mutable_raw)(TensorProto& tensor);

  // model
  const ModelMetaData& (*model_meta_data)(const Model& model);

  // util
  std::string (*data_type_to_string)(int elem_type);
};

#ifndef USE_VITISAI
VAIP_DLL_SPEC const OrtApiForVaip* api();
// avoid macro redefinitions in vitisai ort ep.
#  define VAIP_ORT_API(name)                                                   \
    (::vaip_core::api()->name != nullptr                                       \
         ? ::vaip_core::api()->name                                            \
         : (assert(false && #name " is not set"), nullptr))
#endif
} // namespace vaip_core
