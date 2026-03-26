#pragma once
/**
 * @file adefine.hpp
 * @brief Legacy compatibility shim.
 *
 * MACRO:  REGISTER_MEMORY_DUMP_HANDLER — kept for backward compatibility with
 *         existing code that instantiates MemoryDump via this macro.
 *         Will be removed once Spec 05 (MemoryDump refactor) is complete.
 *
 * The following macros have been REMOVED in favour of proper C++20 solutions:
 *   - PURE      → use `= 0` directly.
 *   - dlog(...) → use atugcc::core::dlog() from <atugcc/core/dlog.hpp> (Spec 06).
 *   - aformat   → use std::format directly (both MSVC and GCC 14+).
 */

// MACRO: backward-compat until Spec 05 lands.
#define REGISTER_MEMORY_DUMP_HANDLER alog::MemoryDump md

// std::format is used directly in new code.
// This alias is kept only so existing files compile; remove after Spec 06.
#ifdef _WIN32
#  define aformat std::format   // MACRO: transitional alias, remove after Spec 06
#elif defined(__linux__)
#  define aformat std::format   // MACRO: transitional alias, remove after Spec 06
#endif