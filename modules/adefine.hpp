#ifndef __ADEFINE__
#define __ADEFINE__

#define PURE =0

#define REGISTER_MEMORY_DUMP_HANDLER alog::MemoryDump md

#ifdef NDEBUG//Release
#define dlog(...) 

#else//Debug
#define dlog(...) alog::DbgBuf::log(__func__, "(): ", __VA_ARGS__)

#endif//!

#ifdef _WIN32
  #define aformat std::format
#elif defined(__linux__)
  #define aformat fmt::format
#endif


#endif//!__ADEFINE__