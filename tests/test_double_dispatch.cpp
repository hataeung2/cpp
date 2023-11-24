#include "gtest/gtest.h"
#include "double_dispatch.hpp"

// EXPECT_EQ (1, 1) << "EQ";
// EXPECT_EQ (true, true) << "EQ";
// EXPECT_NE (true, false) << "NE";
TEST(testSample, double_dispatch_001) {
  SystemA<std::string> sa;
  SystemB<std::string> sb;
  sa.sendDataTo(sb, "hi B");
  EXPECT_EQ("hi B", sb.getLastRecvd());
  sb.sendDataTo(sa, "hi A");
  EXPECT_EQ("hi A", sa.getLastRecvd());
}
