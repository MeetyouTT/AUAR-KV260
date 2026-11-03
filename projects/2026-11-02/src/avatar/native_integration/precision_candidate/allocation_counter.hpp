// SPDX-License-Identifier: AGPL-3.0-only
#pragma once
#include <cstddef>
void track_allocations(bool enabled) noexcept;
std::size_t tracked_allocations() noexcept;
