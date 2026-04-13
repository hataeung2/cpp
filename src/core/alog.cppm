module;

#include "atugcc/core/logger.hpp"

export module alog;

export namespace alog {

using Logger [[deprecated("use atugcc::core::Logger")]] = ::atugcc::core::Logger;

} // namespace alog

