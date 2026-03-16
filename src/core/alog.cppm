/**
 * @brief thread safe log module
 * if crash with unhandled exceptions it dumps the memory 
 * 
 */
module;

export module alog;

#include "atugcc/core/atime.hpp"
#include "atugcc/core/ring_buffer.h"
#include "atugcc/core/memory_dump.hpp"

export namespace alog {
  class RingBuffer;
  class DbgBuf;
  class MemoryDump;

}//!export namespace alog {

