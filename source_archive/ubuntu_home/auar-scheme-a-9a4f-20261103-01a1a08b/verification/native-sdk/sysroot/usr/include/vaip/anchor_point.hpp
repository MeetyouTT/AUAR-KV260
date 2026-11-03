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
#include <gsl/gsl-lite.hpp>
#ifdef _WIN32
#pragma warning(push)
#pragma warning(disable : 4251)
#pragma warning(disable : 4275)
#endif
#include "vaip/anchor_point.pb.h"
#ifdef _WIN32
#pragma warning(pop)
#endif
#include <memory>
namespace vaip_core {

// clang-format off
#define VAIP_CORE_ANCHOR_POINT_TYPES(processor) \
    processor(IDENTITY)                         \
    processor(TRANSPOSE)                        \
    processor(NCHW2NHWC)                        \
    processor(NHWC2NCHW)                        \
    processor(OIHW2OHWI)                        \
    processor(IOHW2OHWI)                        \
    processor(RESHAPE)                          \
    processor(FIX)                              \
    processor(CAST)                              \
    processor(UNKNOWN)
// clang-format on

#define VAIP_CORE_ANCHOR_POINT_ENUM_DEF(name) name,
class AnchorPoint {
public:
  enum Type { VAIP_CORE_ANCHOR_POINT_TYPES(VAIP_CORE_ANCHOR_POINT_ENUM_DEF) };
  struct Description {
    Description(Type type1) : type{type1}, order{} {}
    Description(Type type1, gsl::span<const int64_t> order1)
        : type{type1}, order{order1.begin(), order1.end()} {}
    Type type;
    std::vector<int64_t> order;
  };

  // functions below are only used by graph.cpp
  // std::string is not safe to return across DLL. but we relax this requirement
  // anyway.
public:
  static std::unique_ptr<AnchorPoint> create(const Node& node,
                                             const Description& desciption);
  static std::unique_ptr<AnchorPoint>
      VAIP_DLL_SPEC deserialize(const gsl::span<char>& buffer);

  AnchorPoint();
  virtual ~AnchorPoint();

public:
  // return the original node name on the very first original model.
  virtual std::string node_name() const = 0;
  // get the create shadow name with a suffix to create a new node.
  virtual std::string node_name_suffix() const = 0;
  // merge two anchor point and create an new anchor point.
  virtual std::unique_ptr<AnchorPoint>
  merge_anchor_point(std::unique_ptr<AnchorPoint> other) const = 0;
  // return an op_debug_string represented.
  virtual std::string op_debug_string() const = 0;
  // return a serialized string.
  virtual std::string serialize() const = 0;
  // is it an idenity node or not
  virtual bool is_identity() const = 0;
  // the suffix name of this anchor point, to create a new output args.
  virtual std::string suffix() const = 0;
  virtual const AnchorPointProto& get_proto() const = 0;
};
} // namespace vaip_core
