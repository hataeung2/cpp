/**
 * @brief thread safe log module
 * if crash with unhandled exceptions it dumps the memory 
 * 
 */
module;


#include "atugcc/core/atime.hpp"
#include "atugcc/core/memory_dump.hpp"

export module alog;

export namespace alog {
  class RingBuffer;
  class DbgBuf;
  class MemoryDump;

}//!export namespace alog {

