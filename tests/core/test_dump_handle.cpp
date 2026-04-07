#include <gtest/gtest.h>
#include <fstream>

#include "atugcc/core/ring_buffer.hpp"
#include "atugcc/core/memory_dump.hpp"

using namespace atugcc::core;

TEST(DumpHandleTest, WriteToHandle) {
#ifdef _WIN32
  const std::wstring path = L"test_dump_handle.bin";
  auto res = alog::MemoryDump::prepareDumpFileWin(path);
  ASSERT_TRUE(res.has_value());

  // write a sample log
  DbgBuf::log("test message from DumpHandleTest", Level::Info);

  void* h = alog::MemoryDump::getDumpHandle();
  ASSERT_NE(h, nullptr);

  // Best-effort dump
  DbgBuf::dumpToHandle(h);

  // Verify file was written
  std::ifstream in("test_dump_handle.bin", std::ios::binary);
  ASSERT_TRUE(in.is_open());
  std::string content((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
  ASSERT_FALSE(content.empty());
#else
  GTEST_SKIP() << "Windows-specific test";
#endif
}
