// SPDX-License-Identifier: AGPL-3.0-only
// Test-only separate TU: no allocator replacement in production renderer.
#include "allocation_counter.hpp"
#include <cstdlib>
#include <new>
namespace {bool tracking=false;std::size_t count=0;}
void track_allocations(bool enabled) noexcept {tracking=enabled;if(enabled)count=0;}
std::size_t tracked_allocations() noexcept {return count;}
void* operator new(std::size_t n){if(tracking)++count;if(void* p=std::malloc(n?n:1))return p;throw std::bad_alloc();}
void* operator new[](std::size_t n){return ::operator new(n);}
void operator delete(void* p) noexcept {std::free(p);}
void operator delete[](void* p) noexcept {std::free(p);}
void operator delete(void* p,std::size_t) noexcept {std::free(p);}
void operator delete[](void* p,std::size_t) noexcept {std::free(p);}
