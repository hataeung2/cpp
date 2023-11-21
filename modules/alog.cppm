/**
 * @brief thread safe log module
 * if crash with unhandled exceptions it dumps the memory 
 * 
 */
module;

export module alog;

#include "ring_buffer.h"
#include "memory_dump.hpp"
#include "atime.hpp"

export namespace alog {
  class MemoryDump;
  class DbgBuf;
  class RingBuffer;

}//!export namespace alog {

