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
#ifndef VAIP_EXPORT_DLL
#define VAIP_EXPORT_DLL 0
#endif
#ifndef VAIP_USER
#define VAIP_USER 4
#endif

#if VAIP_EXPORT_DLL == 1
// ok to include by internal cpp files.
#else

#if VAIP_USER == 1 || VAIP_USER == 2 || VAIP_USER == 3
#else
#error "please include vaip/vaip.hpp first"
#endif
#endif
