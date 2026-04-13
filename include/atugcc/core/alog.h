#pragma once

#include "atugcc/core/logger.hpp"

namespace alog {

using Logger [[deprecated("use atugcc::core::Logger from atugcc/core/logger.hpp")]] = ::atugcc::core::Logger;

} // namespace alog