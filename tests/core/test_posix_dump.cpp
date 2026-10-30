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

  // The raw block of the calling thread's buffer holds the message (spec 010-09 D6)
  std::ifstream in(path, std::ios::binary);
  ASSERT_TRUE(in.is_open());
  std::string content((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
  ASSERT_EQ(content.rfind("ATGLBUF1", 0), 0u);
  ASSERT_NE(content.find("posix test message"), std::string::npos);

  // And a full DUMP-V2 dump through the writer used by the crash handlers
  const std::filesystem::path full = "test_posix_dump_full.bin";
  ASSERT_TRUE(alog::MemoryDump::prepareDumpFile(full).has_value());
  alog::MemoryDump::writeDumpNow("manual", 0);
  std::ifstream in2(full, std::ios::binary);
  std::string content2((std::istreambuf_iterator<char>(in2)), std::istreambuf_iterator<char>());
  ASSERT_EQ(content2.rfind("DUMP-V2\n", 0), 0u);
  ASSERT_NE(content2.find("posix test message"), std::string::npos);
  in2.close();
  std::error_code fullEc;
  std::filesystem::remove(full, fullEc);

  // Cleanup
  in.close();
  std::error_code ec;
  std::filesystem::remove(path, ec);
  (void)ec;
#else
  GTEST_SKIP() << "POSIX-specific test";
#endif
}
