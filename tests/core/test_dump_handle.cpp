#include <gtest/gtest.h>
#include <fstream>
#include <filesystem>

#include "atugcc/core/ring_buffer.hpp"
#include "atugcc/core/memory_dump.hpp"

using namespace atugcc::core;

TEST(DumpHandleTest, WriteToHandle) {
#ifdef _WIN32
  // Ensure log directory exists and prepare dump file paths inside it.
  std::filesystem::create_directories("log");
  const std::filesystem::path p1 = std::filesystem::path("log") / "test_dump_handle.bin";
  const std::wstring path = p1.wstring();
  auto res = alog::MemoryDump::prepareDumpFileWin(path);
  ASSERT_TRUE(res.has_value());

  // write a sample log
  DbgBuf::log("test message from DumpHandleTest", Level::Info);

  void* h = alog::MemoryDump::getDumpHandle();
  ASSERT_NE(h, nullptr);

  // Best-effort dump
  DbgBuf::dumpToHandle(h);

  // Verify file was written
  std::ifstream in(p1.string(), std::ios::binary);
  ASSERT_TRUE(in.is_open());
  std::string content((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
  ASSERT_FALSE(content.empty());

  // Also exercise the crash handler path directly (best-effort):
  // prepare a separate dump file and invoke the inline crash handler.
  const std::filesystem::path p2 = std::filesystem::path("log") / "test_dump_handle_crash.bin";
  const std::wstring crash_path = p2.wstring();
  auto res2 = alog::MemoryDump::prepareDumpFileWin(crash_path);
  ASSERT_TRUE(res2.has_value());
  // Call the crash handler directly with a nullptr EXCEPTION_POINTERS (best-effort)
  crashHdler(nullptr);
  std::ifstream in2(p2.string(), std::ios::binary);
  ASSERT_TRUE(in2.is_open());
  std::string content2((std::istreambuf_iterator<char>(in2)), std::istreambuf_iterator<char>());
  // Expect header marker
  ASSERT_NE(content2.find("DUMP-V1"), std::string::npos);
#else
  GTEST_SKIP() << "Windows-specific test";
#endif
}
