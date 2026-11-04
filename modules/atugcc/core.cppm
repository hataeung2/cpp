// Module atugcc.core: the public core API for `import atugcc.core;` (spec 070-13).
//
// A wrapper module: the global module fragment includes the public core headers and the
// module exports their public names with using-declarations. The headers stay the source
// of truth, so a source that includes them and imports this module sees one entity per name.
// Not exported: detail::, the ring buffer's block-header helpers and constants, and macros
// (a module cannot export a macro; include the header that defines it).
// In a source that uses both forms, every #include comes before every import.
module;

#include "atugcc/core/error.hpp"
#include "atugcc/core/log_buffer_config.hpp"
#include "atugcc/core/logger.hpp"
#include "atugcc/core/ring_buffer.hpp"
#include "atugcc/core/timestamp.hpp"

export module atugcc.core;

export namespace atugcc::core {
// error.hpp
using ::atugcc::core::CoreError;
using ::atugcc::core::to_string;
using ::atugcc::core::Expected;
using ::atugcc::core::Result;
// logger.hpp
using ::atugcc::core::FormatWithLocation;
using ::atugcc::core::Logger;
// log_buffer_config.hpp
using ::atugcc::core::Delivery;
using ::atugcc::core::OverflowPolicy;
using ::atugcc::core::Durability;
using ::atugcc::core::LogBufferConfig;
using ::atugcc::core::configureLogBuffers;
using ::atugcc::core::currentLogBufferConfig;
using ::atugcc::core::LogMapRecovery;
using ::atugcc::core::recoverLogMaps;
// ring_buffer.hpp
using ::atugcc::core::Level;
using ::atugcc::core::RingBuffer;
using ::atugcc::core::DbgBuf;
using ::atugcc::core::makeRingBuffer;
// timestamp.hpp
using ::atugcc::core::TimeStamp;
using ::atugcc::core::operator|;
} // namespace atugcc::core
