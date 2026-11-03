// A small C ABI around the installed Vitis AI 3.0 YOLOvX implementation.
// Letterbox, quantization, DPU execution, decoding and NMS stay in that library.
#include <algorithm>
#include <cstdio>
#include <exception>
#include <memory>
#include <opencv2/core.hpp>
#include <vitis/ai/yolovx.hpp>

namespace {
thread_local char error_text[512] = {};
struct Detector {
  std::unique_ptr<vitis::ai::YOLOvX> model;
};
void error(const char* value) {
  std::snprintf(error_text, sizeof(error_text), "%s", value);
}
}

extern "C" {
int aura_yolox_abi() { return 1; }
const char* aura_yolox_error() { return error_text; }
void* aura_yolox_create(const char* model_path) {
  error_text[0] = 0;
  try {
    if (!model_path || !*model_path) {
      error("Missing model path");
      return nullptr;
    }
    auto detector = std::make_unique<Detector>();
    detector->model = vitis::ai::YOLOvX::create(model_path, true);
    if (!detector->model || detector->model->getInputWidth() != 416 ||
        detector->model->getInputHeight() != 416 ||
        detector->model->get_input_batch() != 1) {
      error("Expected a batch-one 416x416 YOLOX-Nano model");
      return nullptr;
    }
    return detector.release();
  } catch (const std::exception& exc) {
    error(exc.what());
    return nullptr;
  } catch (...) {
    error("Unknown native create error");
    return nullptr;
  }
}

// Output rows are original-image x1,y1,x2,y2,score,COCO class ID.
int aura_yolox_detect(void* handle, const unsigned char* bgr, int width,
                     int height, int stride, float* output, int capacity,
                     int class_id, int* count) {
  error_text[0] = 0;
  if (count) *count = 0;
  if (!handle || !bgr || !output || !count || width <= 0 || width > 4096 ||
      height <= 0 || height > 4096 || stride < width * 3 ||
      capacity <= 0 || capacity > 300 || class_id != 0) {
    error("Invalid person-detection input");
    return -1;
  }
  try {
    cv::Mat image(height, width, CV_8UC3, const_cast<unsigned char*>(bgr), stride);
    auto result = static_cast<Detector*>(handle)->model->run(image);
    std::stable_sort(result.bboxes.begin(), result.bboxes.end(),
                     [](const auto& a, const auto& b) { return a.score > b.score; });
    for (const auto& box : result.bboxes) {
      if (box.label != class_id || box.box.size() != 4) continue;
      if (*count >= capacity) break;
      float* row = output + (*count) * 6;
      std::copy(box.box.begin(), box.box.end(), row);
      row[4] = box.score;
      row[5] = static_cast<float>(box.label);
      ++*count;
    }
    return 0;
  } catch (const std::exception& exc) {
    error(exc.what());
    return -1;
  } catch (...) {
    error("Unknown native inference error");
    return -1;
  }
}

void aura_yolox_destroy(void* handle) { delete static_cast<Detector*>(handle); }
}
