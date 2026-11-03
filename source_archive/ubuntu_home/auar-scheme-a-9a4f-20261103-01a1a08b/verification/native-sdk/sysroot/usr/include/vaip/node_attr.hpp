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
class NodeAttr {
public:
  VAIP_DLL_SPEC NodeAttr(const std::string& name, int64_t value);
  VAIP_DLL_SPEC NodeAttr(const std::string& name, float value);
  VAIP_DLL_SPEC NodeAttr(const std::string& name, const std::string& value);
  VAIP_DLL_SPEC NodeAttr(const std::string& name, const TensorProto& value);

  VAIP_DLL_SPEC NodeAttr(const std::string& name,
                         const std::vector<int64_t>& value);
  VAIP_DLL_SPEC NodeAttr(const std::string& name,
                         const std::vector<float>& value);
  VAIP_DLL_SPEC NodeAttr(const std::string& name,
                         const std::vector<std::string>& value);
  VAIP_DLL_SPEC NodeAttr(const std::string& name, AttributeProtoPtr ptr);

  VAIP_DLL_SPEC AttributeProto& get();
  VAIP_DLL_SPEC const AttributeProto& get() const;

private:
  AttributeProtoPtr attribute_proto_;
};

class NodeAttributesBuilder {
public:
  VAIP_DLL_SPEC explicit NodeAttributesBuilder(size_t capacity = 10);
  VAIP_DLL_SPEC
  NodeAttributesBuilder(const NodeAttributesBuilder&) = delete;
  VAIP_DLL_SPEC
  NodeAttributesBuilder(NodeAttributesBuilder&&) = default;
  /// after build, all attrs_ are cleared.
  VAIP_DLL_SPEC NodeAttributesPtr build();
  /// for efficiency reason, after merge_into, all attrs_ are
  /// moved.
  VAIP_DLL_SPEC void merge_into(Node& node);
  VAIP_DLL_SPEC void merge_into(NodeAttributes& attrs);
  template <typename T>
  NodeAttributesBuilder& add(const std::string& name, T&& value) {
    attrs_.emplace_back(name, std::forward<T>(value));
    return *this;
  }

private:
  std::vector<NodeAttr> attrs_;
};
VAIP_DLL_SPEC AttributeProtoPtr attr_proto_clone(const AttributeProto& attr);
VAIP_DLL_SPEC AttributeProtoPtr
attr_proto_new_ints(const std::string& name, const std::vector<int64_t>& attr);
} // namespace vaip_core
