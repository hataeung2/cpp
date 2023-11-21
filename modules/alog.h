#ifndef __ALOG__
#define __ALOG__

#include "ring_buffer.h"
#include "memory_dump.h"
#include "atime.hpp"

#ifdef _WIN32
#define EXPORT export
#else
#define EXPORT
#endif
EXPORT namespace alog {
  class MemoryDump;
  class DbgBuf;
  class RingBuffer;

}//!EXPORT namespace alog {

#endif//!__ALOG__