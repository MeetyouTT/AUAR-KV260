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
#include "./node_attr.hpp"
#include "./vaip_ort_api.hpp"
#include "vaip/node.hpp"
#include <type_traits>
#ifdef _WIN32
#  pragma warning(push)
#  pragma warning(disable : 4251)
#  pragma warning(disable : 4275)
#endif
#include "vaip/config.pb.h"
#ifdef _WIN32
#  pragma warning(pop)
#endif
#include <filesystem>
#include <memory>
#include <string>
namespace onnxruntime {
class Node;
class Graph;
class GraphViewer;
class NodeArg;
class Model;
} // namespace onnxruntime
namespace vaip_core {
#define PASS_LOG(self_, n)                                                     \
  LOG_IF(INFO, (self_.get_pass_proto().enable_log() &&                         \
                self_.get_pass_proto().log_verbosity() >= n))
using namespace onnxruntime;
struct ConstDataInfo {
  size_t offset;
  size_t size;
};
class IPass {
public:
  using action_t = std::function<void(IPass& self, Graph& graph)>;
  using node_action_t =
      std::function<bool(IPass& self, Graph& graph, const Node& node)>;

  IPass() = default;
  virtual ~IPass() = default;

public:
  virtual void* get_state() = 0;
  virtual const std::filesystem::path& get_log_path() const = 0;
  virtual void set_fix_info(const char* name, int fix_pos) = 0;
  virtual int get_fix_info(const char* name) const = 0;
  virtual bool has_fix_info(const char* name) const = 0;
  virtual void create_const(const char* name, gsl::span<const char> data) = 0;
  inline void create_const(const Node& node, gsl::span<const char> data) {
    auto name = node_get_output_name(node);
    create_const(name.c_str(), data);
  }
  virtual void create_empty_const(const char* name, size_t size) = 0;
  inline void create_empty_const(const Node& node, size_t size) {
    auto name = node_get_output_name(node);
    create_empty_const(name.c_str(), size);
  }
  virtual void
  create_lazy_const(const char* name, size_t size,
                    const std::function<void(gsl::span<char>)>& lazy) = 0;
  inline void
  create_lazy_const(const Node& node, size_t size,
                    const std::function<void(gsl::span<char>)>& lazy) {
    create_lazy_const(node_get_output_name(node).c_str(), size, lazy);
  }
  virtual void create_const_alias(const char* alias_name, const char* name) = 0;
  inline void create_const_alias(const Node& new_node, const Node& origin) {
    auto alias = VAIP_ORT_API(node_get_output_name)(new_node);
    auto name = VAIP_ORT_API(node_get_output_name)(origin);
    create_const_alias(alias.c_str(), name.c_str());
  }
  virtual bool has_const(const char* name) const = 0;
  virtual ConstDataInfo get_const_info(const char* name) const = 0;
  // eval lazy function after we invoke get_const_data_ptr.
  virtual void* get_const_data_ptr(const char* name, bool force) const = 0;
  template <typename T> inline gsl::span<T> get_const_data(const char* name) {
    auto info = get_const_info(name);
    auto ptr = get_const_data_ptr(name, true /*force*/);
    return gsl::span<T>(reinterpret_cast<T*>(ptr), info.size / sizeof(T));
  }
  template <typename T> inline gsl::span<T> get_const_data(const Node& node) {
    auto name = node_get_output_name(node);
    return get_const_data<T>(name.c_str());
  }
  template <typename T>
  inline gsl::span<T> get_const_data(const NodeArg& node_arg) {
    auto name = VAIP_ORT_API(node_arg_get_name)(node_arg);
    return get_const_data<T>(name.c_str());
  }

  virtual void dump_fix_info(const char* name) const = 0;
  virtual void dump_const_info(const char* name) const = 0;
  virtual void dump_const_data(const char* name) const = 0;
  virtual const PassProto& get_pass_proto() const = 0;

  virtual std::vector<AttributeProtoPtr>&
  node_extra_attrs(const char* name) = 0;
  inline void node_add_extra_attr(const char* name, const NodeAttr& attr) {
    node_extra_attrs(name).push_back(attr_proto_clone(attr.get()));
  }

  virtual Node& fuse(Graph& graph, const std::string& name,
                     const std::string& op_type,
                     const std::vector<size_t>& nodes,
                     const std::vector<std::string>& inputs,
                     const std::vector<std::string>& outputs,
                     const std::vector<std::string>& constant_initializers,
                     const std::string& device) = 0;

public:
  VAIP_DLL_SPEC
  void copy_fix_info(const Node& from_node, const Node& to_node);
  void copy_fix_info(const char* from, const char* to);
};

struct PassInfo {
  typedef union {
    void* __p; // ease of union initialization;
    bool (*process_node)(IPass& self, Graph& graph, const Node& node);
    void (*process_graph)(IPass& self, Graph& graph);
  } process_t;
  typedef struct {
    int type;
    process_t proc;
  } process_def;
  void* (*init)(IPass& self);
  void (*deinit)(void*);
  typedef void (*preprocess_t)(void* state, IPass& self, Graph& graph);
  preprocess_t preprocess;
  typedef void (*postprocess_t)(void* state, IPass& self, Graph& graph);
  postprocess_t postprocess;
  size_t size;
#ifdef _WIN32
#  pragma warning(push)
#  pragma warning(disable : 4200)
#else
#  pragma GCC diagnostic push
#  pragma GCC diagnostic ignored "-Wpedantic"
#endif
  process_def processes[];
#ifdef _WIN32
#  pragma warning(pop)
#else
#  pragma GCC diagnostic pop
#endif

  IPass::action_t get_action(size_t index) const;
};
template <typename T, class = void> struct has_preprocess_t {
  static constexpr PassInfo::preprocess_t preprocess = nullptr;
};

template <typename T>
struct has_preprocess_t<T,
                        std::void_t<decltype(std::declval<T*>()->preprocess(
                            std::declval<IPass&>(), std::declval<Graph&>()))>>
    : public std::true_type {
  static constexpr PassInfo::preprocess_t preprocess =
      [](void* self, IPass& pass, Graph& graph) {
        static_cast<T*>(self)->preprocess(pass, graph);
      };
};

template <typename T, class = void> struct has_postprocess_t {
  static constexpr PassInfo::postprocess_t postprocess = nullptr;
};

template <typename T>
struct has_postprocess_t<T,
                         std::void_t<decltype(std::declval<T*>()->postprocess(
                             std::declval<IPass&>(), std::declval<Graph&>()))>>
    : public std::true_type {
  static constexpr PassInfo::postprocess_t postprocess =
      [](void* self, IPass& pass, Graph& graph) {
        static_cast<T*>(self)->postprocess(pass, graph);
      };
};
template <typename Pass> struct CommonInitAndDeinit {
  static void* init(IPass& self) {
    auto state = new Pass(self);
    return (void*)state;
  }
  static void deinit(void* state) { delete static_cast<Pass*>(state); }
};

template <typename T, class = void> struct has_process_t {
  // not defined
  // static constexpr int type = -1;
  // static constexpr void* process = nullptr;
};

template <typename T>
struct has_process_t<T, std::void_t<decltype(std::declval<T*>()->process(
                            std::declval<IPass&>(), std::declval<Graph&>()))>>
    : public std::true_type {
  static constexpr int type = 0;
  static void process(IPass& self, Graph& graph) {
    static_cast<T*>(self.get_state())->process(self, graph);
  }
};

template <typename T>
struct has_process_t<
    T, std::enable_if_t<std::is_same_v<
           bool, decltype(std::declval<T*>()->process(
                     std::declval<IPass&>(), std::declval<Graph&>(),
                     std::declval<const Node&>()))>>> : public std::true_type {
  static constexpr int type = 1;
  static bool process(IPass& self, Graph& graph, const Node& node) {
    return static_cast<T*>(self.get_state())->process(self, graph, node);
  }
};

template <typename Pass> struct ProcessorPassInfo {
  static vaip_core::PassInfo* pass_info() { return &info; }
  static PassInfo info;
};

#ifndef _WIN32
#  pragma GCC diagnostic push
#  pragma GCC diagnostic ignored "-Wpedantic"
#endif
template <typename Pass>
PassInfo ProcessorPassInfo<Pass>::info = {
    CommonInitAndDeinit<Pass>::init,
    CommonInitAndDeinit<Pass>::deinit,
    has_preprocess_t<Pass>::preprocess,
    has_postprocess_t<Pass>::postprocess,
    1,
    {
        {has_process_t<Pass>::type, {(void*)has_process_t<Pass>::process}},
    }};
#ifndef _WIN32
#  pragma GCC diagnostic pop
#endif

namespace fs = std::filesystem;
using namespace onnxruntime;

IPass::action_t
create_action_from_node_action(IPass::node_action_t node_action);
IPass::action_t create_xmodel_process_graph(IPass::action_t action);
} // namespace vaip_core

#if VAIP_USE_DLL == 1
#  define DEFINE_VAIP_PASS(cls, id)                                            \
    extern "C" VAIP_PASS_ENTRY vaip_core::PassInfo* vaip_pass_info() {         \
      return ProcessorPassInfo<cls>::pass_info();                              \
    }                                                                          \
    extern "C" {                                                               \
    void* /* a hook var*/ id##__hook = nullptr;                                \
    }
#else
#  include <vitis/ai/plugin.hpp>
#  define DEFINE_VAIP_PASS(cls, id)                                            \
    static vaip_core::PassInfo* vaip_pass_info() {                             \
      return ProcessorPassInfo<cls>::pass_info();                              \
    }                                                                          \
    namespace {                                                                \
    static vitis::ai::StaticPluginRegister                                     \
        __register(OUTPUT_NAME, "vaip_pass_info", (void*)&vaip_pass_info);     \
    }                                                                          \
    extern "C" {                                                               \
    void* /* a hook var*/ id##__hook = &__register;                            \
    }

#endif
