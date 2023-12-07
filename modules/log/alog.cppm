/**
 * @brief thread safe log module
 * if crash with unhandled exceptions it dumps the memory 
 * 
 */
module;

export module alog;

#include "atime.hpp"
#include "ring_buffer.h"
#include "memory_dump.hpp"

export namespace alog {
  class RingBuffer;
  class DbgBuf;
  class MemoryDump;

}//!export namespace alog {

