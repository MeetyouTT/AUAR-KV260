/* Copyright 2019 Xilinx Inc.
**
** Licensed under the Apache License, Version 2.0 (the "License");
** you may not use this file except in compliance with the License.
** You may obtain a copy of the License at
**
**     http://www.apache.org/licenses/LICENSE-2.0
**
** Unless required by applicable law or agreed to in writing, software
** distributed under the License is distributed on an "AS IS" BASIS,
** WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
** See the License for the specific language governing permissions and
** limitations under the License.
*/
#pragma once
#include <iostream>
// it trigger VS2019 error
// error LNK1189: the limit of 65535 objects or members in a library has been
// exceeded
#if defined(_WIN32)
#  if XCOMPILER_USE_DLL == 1
#    ifdef XCOMPILER_EXPORT
#      define XCOMPILER_DLLESPEC __declspec(dllexport)
#    else
#      define XCOMPILER_DLLESPEC __declspec(dllimport)
#    endif
#  else
#    define XCOMPILER_DLLESPEC
#  endif
#else
#  define XCOMPILER_DLLESPEC __attribute__((visibility("default")))
#endif

#include "xir/attrs/attrs.hpp"
#include "xir/graph/graph.hpp"
namespace xcompiler {
XCOMPILER_DLLESPEC xir::Graph* run_xcompiler(
    xir::Graph* graph, std::unique_ptr<xir::Attrs> configures);
}  // namespace xcompiler
