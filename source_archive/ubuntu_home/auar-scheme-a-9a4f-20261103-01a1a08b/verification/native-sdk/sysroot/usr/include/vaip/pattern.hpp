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
#include <functional>
#include <initializer_list>
#include <map>
#include <memory>
#include <unordered_map>

namespace vaip_core {

class Binder {
public:
  Binder() {}
  Binder(Binder&&) = default;
  NodeInput operator[](size_t index) const {
    auto it = store_.find((int)index);
    return it == store_.end() ? NodeInput{nullptr, nullptr} : it->second;
  }

private:
  Binder(const std::map<int, const NodeInput>& store)
      : store_(store.begin(), store.end()) {}

  bool has(int id) const { return store_.find(id) != store_.end(); }

  std::unique_ptr<Binder> add(int id, const NodeInput& node_input) const;

  friend class Pattern;
  friend class PatternWildcard;
  friend class PatternConstant;
  friend class PatternNode;
  friend class PatternOr;
  friend class PatternWhere;
  friend class PatternGraphInput;

private:
  std::map<int, const NodeInput> store_;
};

using binder_t = Binder;
using binder_ptr_t = std::unique_ptr<binder_t>;

class Pattern {
public:
  explicit Pattern(int id);
  virtual ~Pattern();
  int get_id() const { return id_; }

  virtual std::string debug_string() const;

  VAIP_DLL_SPEC binder_ptr_t match(const onnxruntime::Graph& graph,
                                   const onnxruntime::Node& node) const;

  binder_ptr_t match_cached(const onnxruntime::Graph& graph,
                            const NodeInput& node_input,
                            binder_ptr_t cached_binder) const;
  virtual std::string virtualize_label() const;

protected:
  virtual binder_ptr_t match_uncached(const onnxruntime::Graph& graph,
                                      const NodeInput& node_input,
                                      binder_ptr_t cached_binder) const = 0;

private:
  int id_;
};

struct OpTypePattern {
  OpTypePattern(const char* op_type) : op_type_{op_type}, is_optional_{false} {}
  OpTypePattern(const std::string& op_type)
      : op_type_{op_type}, is_optional_{false} {}
  OpTypePattern(const std::string& op_type, bool is_optional)
      : op_type_{op_type}, is_optional_{is_optional} {}
  OpTypePattern(const char* op_type, bool is_optional)
      : op_type_{op_type}, is_optional_{is_optional} {}
  std::string op_type_;
  bool is_optional_;
};

struct PatternBuilder {
  VAIP_DLL_SPEC std::unique_ptr<Pattern> wildcard();
  VAIP_DLL_SPEC std::unique_ptr<Pattern>
  node2(const std::string& op_type,
        const std::vector<std::shared_ptr<Pattern>>& args);
  VAIP_DLL_SPEC std::unique_ptr<Pattern>
  node3(const std::string& op_type,
        const std::vector<std::shared_ptr<Pattern>>& args,
        const std::vector<std::shared_ptr<Pattern>>& optional_args);
  VAIP_DLL_SPEC std::vector<std::shared_ptr<Pattern>>
  chain2(const std::vector<OpTypePattern>& ops,
         const std::vector<std::shared_ptr<Pattern>>& args);

  VAIP_DLL_SPEC std::unique_ptr<Pattern>
  Or(const std::vector<std::shared_ptr<Pattern>>& args);
  VAIP_DLL_SPEC std::unique_ptr<Pattern> constant();
  VAIP_DLL_SPEC std::unique_ptr<Pattern> graph_input();
  VAIP_DLL_SPEC std::unique_ptr<Pattern> xir_const_op();
  /// `where` swallows the arg `pattern`. It has same id as pattern.
  std::unique_ptr<Pattern>
  where(std::unique_ptr<Pattern> pattern,
        std::function<bool(const NodeInput&)> test_on_node_input);
  /// Problems: when construction a composite pattern, we need use raw
  /// pointer to access the sub-pattern.
  VAIP_DLL_SPEC void bind(const std::string& name, const Pattern* pat);
  VAIP_DLL_SPEC int get_id(const std::string& name) const;
  VAIP_DLL_SPEC void bindings(std::unordered_map<std::string, int>& ret) const;

private:
  int id_counter_ = 0;
  std::unordered_map<std::string, int> id_map_;
};
} // namespace vaip_core
