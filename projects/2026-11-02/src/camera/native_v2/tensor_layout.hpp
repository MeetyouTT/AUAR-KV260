#pragma once
#include <cstddef>
#include <cstdint>
#include <stdexcept>
#include <vector>

namespace aura {
class Int8Layout {
 public:
  static constexpr std::size_t maximum_bytes = 64 * 1024 * 1024;
  explicit Int8Layout(std::vector<std::int32_t> shape) : shape_(std::move(shape)) {
    if (shape_.empty() || shape_.size() > 8 || shape_[0] != 1)
      throw std::invalid_argument("Batch-one tensor rank required");
    bytes_ = 1;
    for (auto dimension : shape_) {
      if (dimension <= 0 || static_cast<std::size_t>(dimension) > maximum_bytes / bytes_)
        throw std::invalid_argument("Tensor dimensions exceed bounded INT8 storage");
      bytes_ *= static_cast<std::size_t>(dimension);
    }
  }
  std::size_t bytes() const { return bytes_; }
  const std::vector<std::int32_t>& shape() const { return shape_; }
  std::size_t offset(const std::vector<std::int32_t>& index) const {
    if (index.empty()) return 0;
    if (index.size() != shape_.size()) throw std::out_of_range("Tensor index rank mismatch");
    std::size_t offset = 0;
    for (std::size_t i = 0; i < shape_.size(); ++i) {
      if (index[i] < 0 || index[i] >= shape_[i]) throw std::out_of_range("Tensor index outside shape");
      offset = offset * static_cast<std::size_t>(shape_[i]) + static_cast<std::size_t>(index[i]);
    }
    return offset;
  }
 private:
  std::vector<std::int32_t> shape_;
  std::size_t bytes_ = 0;
};
}  // namespace aura
