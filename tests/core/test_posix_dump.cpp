#include <gtest/gtest.h>
#include <fstream>
#include <filesystem>

#include "atugcc/core/ring_buffer.hpp"
#include "atugcc/core/memory_dump.hpp"

using namespace atugcc::core;

TEST(PosixDumpTest, PrepareAndDumpToFd) {
#if defined(__linux__) || defined(__unix__) || defined(__APPLE__)
  const std::filesystem::path path = "test_posix_dump.bin";
  // Prepare the dump file (POSIX)
  auto res = alog::MemoryDump::prepareDumpFile(path);
  ASSERT_TRUE(res.has_value());

  // Write a sample log into the thread-local buffer
  DbgBuf::log("posix test message", Level::Info);

  int fd = alog::MemoryDump::getDumpFd();
  ASSERT_GE(fd, 0);

  // Perform the dump (best-effort)
  DbgBuf::dumpToFd(fd);

  // Verify the file contains something
  std::ifstream in(path, std::ios::binary);
  ASSERT_TRUE(in.is_open());
  std::string content((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
  ASSERT_FALSE(content.empty());

  // Cleanup
  in.close();
  std::error_code ec;
  std::filesystem::remove(path, ec);
  (void)ec;
#else
  GTEST_SKIP() << "POSIX-specific test";
#endif
}
