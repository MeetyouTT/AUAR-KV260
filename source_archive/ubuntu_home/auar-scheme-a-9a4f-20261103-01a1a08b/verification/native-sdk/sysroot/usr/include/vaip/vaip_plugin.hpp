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
#include "./export.hpp"
#include <memory>
#include <string>
#include <unordered_map>
namespace vaip_core {

struct Plugin {
  VAIP_DLL_SPEC Plugin(const char* name);
  VAIP_DLL_SPEC ~Plugin();
  template <typename R, typename... Args>
  R invoke(const char* name, Args... args) {
    auto sym = my_plugin_sym(plugin_, name);
#if defined(CHECK)
    CHECK(sym != nullptr) << "no such function: " << name << "; " //
                          << "libname " << name_ << " "           //
                          << "so_name " << so_name_ << " "        //
        ;
#else
#ifndef USE_VITISAI
#warning "it would be better to include <glog/logging.h>"
#endif
#endif
    typedef R (*fun_type_t)(Args...);
    fun_type_t f = reinterpret_cast<fun_type_t>(sym);
    return f(std::forward<Args>(args)...);
  }
  static Plugin* get(const std::string& name);

private:
  std::string name_;
  std::string so_name_;
  void* plugin_;

private:
  static std::string guess_name(const char* name);
  static std::unordered_map<std::string, std::shared_ptr<Plugin>> store_;
  void* my_plugin_sym(void*, const char*);
};

template <typename T, typename... Args> class WithPlugin {
public:
  static std::unique_ptr<T> create(const std::string& plugin_name,
                                   Args... args) {
    auto plugin = Plugin::get(plugin_name);
    auto ret = plugin->invoke<T*>(T::entry_point, args...);
    return std::unique_ptr<T>(ret);
  }
};
} // namespace vaip_core
