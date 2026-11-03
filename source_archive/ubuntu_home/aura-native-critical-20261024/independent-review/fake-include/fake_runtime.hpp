// Minimal fake compile/runtime surface for bridge ownership tests only.
#pragma once
#include <cstdint>
#include <memory>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <utility>
#include <vector>
namespace xir {
struct DataType { enum Type { XINT };Type type=XINT;int bit_width=8; };
class Tensor {
 public:
  Tensor(std::string name,std::vector<std::int32_t> shape) : name_(std::move(name)),shape_(std::move(shape)) {}
  std::vector<std::int32_t> get_shape() const { return shape_; }
  DataType get_data_type() const { return {}; }
  std::int64_t get_data_size() const { std::int64_t size=1;for(auto d:shape_)size*=d;return size; }
  const std::string& get_name() const { return name_; }
  bool has_attr(const std::string&) const { return true; }
  template<class T> T get_attr(const std::string&) const { return T(7); }
 private:
  std::string name_;std::vector<std::int32_t> shape_;
};
class Subgraph {
 public:
  bool has_attr(const std::string&) const { return true; }
  template<class T> T get_attr(const std::string&) const {
    if constexpr(std::is_same<T,std::string>::value)return "DPU";
    else return T(0x101000056010407ULL);
  }
  std::vector<const Subgraph*> get_children() const { return {this}; }
};
class Graph {
 public:
  static std::unique_ptr<Graph> deserialize(const char*) { return std::make_unique<Graph>(); }
  const Subgraph* get_root_subgraph() const { return &root_; }
 private:Subgraph root_;
};
}  // namespace xir
namespace vart {
class TensorBuffer {
 public:
  explicit TensorBuffer(const xir::Tensor* tensor) : tensor_(tensor) {}
  virtual ~TensorBuffer()=default;
  virtual std::pair<std::uint64_t,std::size_t> data(const std::vector<std::int32_t> = {})=0;
  const xir::Tensor* get_tensor() const { return tensor_; }
 private:const xir::Tensor* tensor_;
};
class Runner {
 public:
  virtual ~Runner()=default;
  static std::unique_ptr<Runner> create_runner(const xir::Subgraph*,const char*);
  virtual std::vector<const xir::Tensor*> get_input_tensors()=0;
  virtual std::vector<const xir::Tensor*> get_output_tensors()=0;
  virtual std::pair<std::uint32_t,int> execute_async(const std::vector<TensorBuffer*>&,const std::vector<TensorBuffer*>&)=0;
  virtual int wait(int,int)=0;
};
}  // namespace vart
