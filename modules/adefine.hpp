#ifndef __ADEFINE__
#define __ADEFINE__

#define REGISTER_MEMORY_DUMP_HANDLER alog::MemoryDump md

#ifdef NDEBUG//Release
#define dlog(...) 

#else//Debug
#define dlog(...) alog::DbgBuf::log(__func__, "(): ", __VA_ARGS__)

#endif//!



#endif//!__ADEFINE__