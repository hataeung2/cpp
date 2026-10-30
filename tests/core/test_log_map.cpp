#include <gtest/gtest.h>

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <format>
#include <fstream>
#include <memory>
#include <new>
#include <random>
#include <string>
#include <string_view>
#include <vector>

#include "atugcc/core/detail/log_map.hpp"
#include "atugcc/core/detail/thread_log_buffer.hpp"
#include "atugcc/core/log_buffer_config.hpp"
#include "atugcc/core/ring_buffer.hpp"

namespace {

using atugcc::core::Level;
using atugcc::core::LogMapRecovery;
using atugcc::core::recoverLogMaps;
namespace detail = atugcc::core::detail;
namespace fs = std::filesystem;

inline constexpr std::string_view kTestMapFileName = "atugcc-4242-20261030T120000000.logmap";
inline constexpr std::uint32_t kTestPid = 4242;
inline constexpr std::size_t kAlign64 = 64;

// 2026-10-30 12:00:00.000 UTC -> 20261030T120000000
inline std::uint64_t testStartSystemNs() noexcept {
    const auto sysDays = std::chrono::sys_days{std::chrono::year{2026} / std::chrono::October / 30};
    const auto sysTime = sysDays + std::chrono::hours{12};
    return static_cast<std::uint64_t>(
        std::chrono::duration_cast<std::chrono::nanoseconds>(sysTime.time_since_epoch()).count());
}

inline constexpr std::uint64_t kTestSteadyBaseNs = 1'000'000'000ULL;

struct AlignedDeleter {
    void operator()(std::byte* p) const noexcept {
        ::operator delete[](p, std::align_val_t{kAlign64});
    }
};

using AlignedStoragePtr = std::unique_ptr<std::byte[], AlignedDeleter>;

class MapImage {
public:
    explicit MapImage(std::size_t totalBytes = detail::kMinMappedBytes)
        : totalBytes_(totalBytes),
          storage_(static_cast<std::byte*>(::operator new[](totalBytes, std::align_val_t{kAlign64}))),
          header_{} {
        std::memset(storage_.get(), 0, totalBytes_);

        std::memcpy(header_.magic, detail::kMapMagic.data(), detail::kMapMagic.size());
        header_.version = detail::kMapVersion;
        header_.arenaOffset = detail::kArenaOffset;
        header_.fileBytes = totalBytes_;
        header_.pid = kTestPid;
        header_.flags = 0;
        header_.startSystemNs = testStartSystemNs();
        header_.steadyBaseNs = kTestSteadyBaseNs;
        // 5 s after the start: record times come from this base pair, the header's "started" from
        // startSystemNs, so reading one in place of the other changes the expected text.
        header_.systemBaseNs = static_cast<std::int64_t>(header_.startSystemNs) + 5'000'000'000LL;
        header_.arenaUsed = detail::kArenaOffset;
        header_.labelCount = detail::kLabelCount;
        header_.labelBytes = detail::kLabelBytes;
    }

    void setFlags(std::uint32_t flags) noexcept {
        header_.flags = flags;
    }

    void setFileBytes(std::uint64_t fileBytes) noexcept {
        header_.fileBytes = fileBytes;
    }

    detail::MapHeader& header() noexcept {
        return header_;
    }

    const detail::MapHeader& header() const noexcept {
        return header_;
    }

    void setLabel(std::uint16_t id, std::string_view text) noexcept {
        if (id >= detail::kLabelCount) {
            return;
        }
        const std::size_t offset = detail::kLabelTableOffset + static_cast<std::size_t>(id) * sizeof(detail::LabelEntry);
        detail::LabelEntry entry{};
        entry.id = id;
        const std::size_t copyLen = std::min(text.size(), static_cast<std::size_t>(detail::kLabelTextBytes));
        entry.len = static_cast<std::uint16_t>(copyLen);
        std::memcpy(entry.text, text.data(), copyLen);
        std::memcpy(storage_.get() + offset, &entry, sizeof(entry));
    }

    detail::ThreadLogBuffer* addBuffer(std::uint32_t slotCount, std::uint32_t threadNo = 0) noexcept {
        const std::uint64_t currentOffset = header_.arenaUsed;
        const std::uint64_t bufferBytes = sizeof(detail::BufferHeaderDisk) +
            static_cast<std::uint64_t>(slotCount) * detail::kSlotBytes;
        if (currentOffset + bufferBytes > totalBytes_) {
            return nullptr;
        }

        auto* buf = detail::ThreadLogBuffer::createIn(storage_.get() + currentOffset, slotCount);
        if (buf == nullptr) {
            return nullptr;
        }
        if (threadNo != 0) {
            buf->setThreadNo(threadNo);
        }

        header_.arenaUsed = currentOffset + bufferBytes;
        return buf;
    }

    std::byte* data() noexcept {
        return storage_.get();
    }

    const std::byte* data() const noexcept {
        return storage_.get();
    }

    std::size_t size() const noexcept {
        return totalBytes_;
    }

    // Lets a test claim more of the arena than its buffers use (an isolated size check, AC-6).
    void setArenaUsed(std::uint64_t used) noexcept {
        header_.arenaUsed = used;
    }

    void syncHeader() noexcept {
        std::memcpy(storage_.get(), &header_, sizeof(header_));
    }

    void writeTo(const fs::path& dir, std::string_view fileName = kTestMapFileName) {
        syncHeader();
        const fs::path filePath = dir / fileName;
        std::ofstream out(filePath, std::ios::binary);
        out.write(reinterpret_cast<const char*>(storage_.get()), static_cast<std::streamsize>(totalBytes_));
        out.close();
    }

private:
    std::size_t totalBytes_{0};
    AlignedStoragePtr storage_{nullptr};
    detail::MapHeader header_{};
};

std::string readFileText(const fs::path& path) {
    std::ifstream in(path, std::ios::binary);
    return {std::istreambuf_iterator<char>(in), std::istreambuf_iterator<char>()};
}

std::vector<std::string> readFileLines(const fs::path& path) {
    std::vector<std::string> lines;
    std::ifstream in(path);
    std::string line;
    while (std::getline(in, line)) {
        if (!line.empty() && line.back() == '\r') {
            line.pop_back();
        }
        lines.push_back(line);
    }
    return lines;
}

enum class CorruptionType {
    SlotCountNotPowerOfTwo,
    SlotCountTooSmall,
    SlotCountTooLarge,
    WritePosLessThanReadPos,
    LenGreaterThan232,
    BrokenContinuation
};

} // namespace

class LogMapRecoveryTest : public ::testing::Test {
protected:
    void SetUp() override {
        static std::atomic<std::uint64_t> counter{0};
        static const auto processSalt = []() noexcept -> std::uint64_t {
            std::random_device rd;
            const auto seed = (static_cast<std::uint64_t>(rd()) << 32) ^ static_cast<std::uint64_t>(rd());
            const auto time = static_cast<std::uint64_t>(std::chrono::steady_clock::now().time_since_epoch().count());
            return seed ^ time;
        }();
        const auto id = counter.fetch_add(1);
        testDir_ = fs::temp_directory_path() / std::format("atugcc_logmap_test_{}_{}", processSalt, id);
        std::error_code ec;
        fs::remove_all(testDir_, ec);
        fs::create_directories(testDir_, ec);
    }

    void TearDown() override {
        std::error_code ec;
        fs::remove_all(testDir_, ec);
    }

    fs::path testDir_;
};

TEST_F(LogMapRecoveryTest, ValidFileRecoversUndeliveredAndContext) {
    MapImage image;
    image.setLabel(1, "app.log");
    // logger id 2 is left unlabelled -> "logger#2"
    // logger id 0 is dbgbuf -> "dbgbuf"

    auto* buf1 = image.addBuffer(64, 1);
    ASSERT_NE(buf1, nullptr);
    auto* buf2 = image.addBuffer(64, 2);
    ASSERT_NE(buf2, nullptr);

    const std::uint64_t t1 = kTestSteadyBaseNs + 10'000'000ULL; // 10 ms
    const std::uint64_t t2 = kTestSteadyBaseNs + 20'000'000ULL; // 20 ms
    const std::uint64_t t3 = kTestSteadyBaseNs + 30'000'000ULL; // 30 ms
    const std::uint64_t t4 = kTestSteadyBaseNs + 40'000'000ULL; // 40 ms

    // Buffer 1 (thread 1): rec A (delivered), rec C (undelivered)
    ASSERT_TRUE(buf1->tryWrite(t1, 0, 1, Level::Info, "msg_t1_delivered"));
    buf1->advanceRead(1);
    ASSERT_TRUE(buf1->tryWrite(t3, 1, 0, Level::Debug, "msg_t1_undelivered"));

    // Buffer 2 (thread 2): rec B (delivered), rec D (undelivered)
    ASSERT_TRUE(buf2->tryWrite(t2, 0, 2, Level::Warn, "msg_t2_delivered"));
    buf2->advanceRead(1);
    ASSERT_TRUE(buf2->tryWrite(t4, 1, 1, Level::Error, "msg_t2_undelivered"));

    image.writeTo(testDir_);

    auto res = recoverLogMaps(testDir_);
    ASSERT_TRUE(res.has_value());
    ASSERT_EQ(res.value().size(), 1u);

    const LogMapRecovery& rec = res.value()[0];
    EXPECT_EQ(rec.pid, 4242u);
    EXPECT_EQ(rec.undeliveredLines, 2u);
    EXPECT_EQ(rec.deliveredLines, 2u);
    EXPECT_EQ(rec.skippedBuffers, 0u);
    EXPECT_FALSE(rec.crashHandlerRan);
    EXPECT_TRUE(fs::exists(rec.recoveredFile));
    EXPECT_FALSE(fs::exists(testDir_ / kTestMapFileName));

    const auto lines = readFileLines(rec.recoveredFile);
    ASSERT_EQ(lines.size(), 9u);

    // Exact 5 header lines (Plan D4 step 9)
    EXPECT_EQ(lines[0], "# atugcc recovered log (spec 010-10)");
    EXPECT_EQ(lines[1], "# pid 4242, started 2026-10-30T12:00:00.000000Z, map atugcc-4242-20261030T120000000.logmap");
    EXPECT_EQ(lines[2], "# ended without a clean exit; crash handler: no");
    EXPECT_EQ(lines[3], "# 2 undelivered lines (never reached any sink: not in the log file), 2 delivered lines (context), 0 skipped buffers");
    EXPECT_EQ(lines[4], "# a line delivered just before the end can appear both here as undelivered and in the log file");

    // Ordered lines by (timeNs, threadNo, threadSeq)
    EXPECT_EQ(lines[5], "2026-10-30T12:00:05.010000Z T1 [delivered] app.log msg_t1_delivered");
    EXPECT_EQ(lines[6], "2026-10-30T12:00:05.020000Z T2 [delivered] logger#2 msg_t2_delivered");
    EXPECT_EQ(lines[7], "2026-10-30T12:00:05.030000Z T1 [undelivered] dbgbuf msg_t1_undelivered");
    EXPECT_EQ(lines[8], "2026-10-30T12:00:05.040000Z T2 [undelivered] app.log msg_t2_undelivered");
}

TEST_F(LogMapRecoveryTest, CleanExitFlagRemovesWithoutRecovery) {
    MapImage image;
    image.setFlags(detail::kMapFlagCleanExit);
    auto* buf = image.addBuffer(64, 1);
    ASSERT_NE(buf, nullptr);
    ASSERT_TRUE(buf->tryWrite(kTestSteadyBaseNs, 0, 1, Level::Info, "clean_exit_line"));

    image.writeTo(testDir_);

    auto res = recoverLogMaps(testDir_);
    ASSERT_TRUE(res.has_value());
    EXPECT_TRUE(res.value().empty());
    EXPECT_FALSE(fs::exists(testDir_ / kTestMapFileName));

    std::error_code ec;
    for (const auto& entry : fs::directory_iterator(testDir_, ec)) {
        EXPECT_NE(entry.path().extension(), ".log");
    }
}

TEST_F(LogMapRecoveryTest, CrashFlagReported) {
    MapImage image;
    image.setFlags(detail::kMapFlagCrash);
    auto* buf = image.addBuffer(64, 1);
    ASSERT_NE(buf, nullptr);
    ASSERT_TRUE(buf->tryWrite(kTestSteadyBaseNs, 0, 1, Level::Info, "crash_line"));

    image.writeTo(testDir_);

    auto res = recoverLogMaps(testDir_);
    ASSERT_TRUE(res.has_value());
    ASSERT_EQ(res.value().size(), 1u);
    EXPECT_TRUE(res.value()[0].crashHandlerRan);

    const auto lines = readFileLines(res.value()[0].recoveredFile);
    ASSERT_GE(lines.size(), 3u);
    EXPECT_EQ(lines[2], "# ended without a clean exit; crash handler: yes");
}

TEST_F(LogMapRecoveryTest, BadMagic) {
    MapImage image;
    std::memcpy(image.header().magic, "BADMAGIC", 8);
    image.writeTo(testDir_);

    auto res = recoverLogMaps(testDir_);
    ASSERT_TRUE(res.has_value());
    EXPECT_TRUE(res.value().empty());
    EXPECT_FALSE(fs::exists(testDir_ / kTestMapFileName));
    EXPECT_TRUE(fs::exists(testDir_ / (std::string(kTestMapFileName) + ".corrupt")));

    std::error_code ec;
    for (const auto& entry : fs::directory_iterator(testDir_, ec)) {
        EXPECT_NE(entry.path().extension(), ".log");
    }
}

TEST_F(LogMapRecoveryTest, TruncatedFile) {
    const fs::path filePath = testDir_ / kTestMapFileName;
    const fs::path corruptPath = testDir_ / (std::string(kTestMapFileName) + ".corrupt");

    // Variant 1: Valid MapImage cut to 4096 bytes (magic intact, fileBytes unchanged)
    {
        MapImage image;
        image.syncHeader();
        {
            std::ofstream out(filePath, std::ios::binary);
            out.write(reinterpret_cast<const char*>(image.data()), 4096);
        }

        auto res = recoverLogMaps(testDir_);
        ASSERT_TRUE(res.has_value());
        EXPECT_TRUE(res.value().empty());
        EXPECT_FALSE(fs::exists(filePath));
        EXPECT_TRUE(fs::exists(corruptPath));

        std::error_code ec;
        fs::remove(corruptPath, ec);
        for (const auto& entry : fs::directory_iterator(testDir_, ec)) {
            EXPECT_NE(entry.path().extension(), ".log");
        }
    }

    // Variant 2: fileBytes patched to the cut length (4096) so only `size >= kArenaOffset` rejects it
    {
        MapImage image;
        image.setFileBytes(4096);
        image.syncHeader();
        {
            std::ofstream out(filePath, std::ios::binary);
            out.write(reinterpret_cast<const char*>(image.data()), 4096);
        }

        auto res = recoverLogMaps(testDir_);
        ASSERT_TRUE(res.has_value());
        EXPECT_TRUE(res.value().empty());
        EXPECT_FALSE(fs::exists(filePath));
        EXPECT_TRUE(fs::exists(corruptPath));

        std::error_code ec;
        fs::remove(corruptPath, ec);
        for (const auto& entry : fs::directory_iterator(testDir_, ec)) {
            EXPECT_NE(entry.path().extension(), ".log");
        }
    }
}

TEST_F(LogMapRecoveryTest, WrongFileBytes) {
    MapImage image;
    image.setFileBytes(image.size() + 4096); // fileBytes does not match actual size
    image.writeTo(testDir_);

    auto res = recoverLogMaps(testDir_);
    ASSERT_TRUE(res.has_value());
    EXPECT_TRUE(res.value().empty());
    EXPECT_FALSE(fs::exists(testDir_ / kTestMapFileName));
    EXPECT_TRUE(fs::exists(testDir_ / (std::string(kTestMapFileName) + ".corrupt")));

    std::error_code ec;
    for (const auto& entry : fs::directory_iterator(testDir_, ec)) {
        EXPECT_NE(entry.path().extension(), ".log");
    }
}

TEST_F(LogMapRecoveryTest, OneBadBufferOthersRecovered) {
    const CorruptionType corruptions[] = {
        CorruptionType::SlotCountNotPowerOfTwo,
        CorruptionType::SlotCountTooSmall,
        CorruptionType::SlotCountTooLarge,
        CorruptionType::WritePosLessThanReadPos,
        CorruptionType::LenGreaterThan232,
        CorruptionType::BrokenContinuation
    };

    for (const auto corruption : corruptions) {
        std::error_code ec;
        for (const auto& entry : fs::directory_iterator(testDir_, ec)) {
            fs::remove_all(entry.path(), ec);
        }

        // SlotCountTooLarge: the file must be able to hold a 131072-slot block (32 MiB), otherwise the
        // "block fits before end" check rejects it and the range check is never what decides.
        constexpr std::size_t kLargeImageBytes = 40u * 1024u * 1024u;
        MapImage image(corruption == CorruptionType::SlotCountTooLarge ? kLargeImageBytes : detail::kMinMappedBytes);
        image.setLabel(1, "app.log");

        auto* buf1 = image.addBuffer(64, 1);
        ASSERT_NE(buf1, nullptr);
        auto* buf2 = image.addBuffer(64, 2);
        ASSERT_NE(buf2, nullptr);

        ASSERT_TRUE(buf2->tryWrite(kTestSteadyBaseNs + 200, 0, 1, Level::Info, "buf2_good_rec"));

        std::uint32_t expectedSkippedBuffers = 0;
        std::uint64_t expectedUndeliveredLines = 0;

        switch (corruption) {
        case CorruptionType::SlotCountNotPowerOfTwo: {
            SCOPED_TRACE("SlotCountNotPowerOfTwo");
            ASSERT_TRUE(buf1->tryWrite(kTestSteadyBaseNs + 100, 0, 1, Level::Info, "buf1_rec"));
            auto* diskHdr = reinterpret_cast<detail::BufferHeaderDisk*>(image.data() + detail::kArenaOffset);
            diskHdr->slotCount = 100; // Not a power of two
            expectedSkippedBuffers = 1;
            expectedUndeliveredLines = 1; // Only buf2 recovered
            break;
        }
        case CorruptionType::SlotCountTooSmall: {
            SCOPED_TRACE("SlotCountTooSmall");
            ASSERT_TRUE(buf1->tryWrite(kTestSteadyBaseNs + 100, 0, 1, Level::Info, "buf1_rec"));
            auto* diskHdr = reinterpret_cast<detail::BufferHeaderDisk*>(image.data() + detail::kArenaOffset);
            diskHdr->slotCount = 32; // Power of two, but < 64
            expectedSkippedBuffers = 1;
            expectedUndeliveredLines = 1; // Only buf2 recovered
            break;
        }
        case CorruptionType::SlotCountTooLarge: {
            SCOPED_TRACE("SlotCountTooLarge");
            ASSERT_TRUE(buf1->tryWrite(kTestSteadyBaseNs + 100, 0, 1, Level::Info, "buf1_rec"));
            auto* diskHdr = reinterpret_cast<detail::BufferHeaderDisk*>(image.data() + detail::kArenaOffset);
            diskHdr->slotCount = 131072; // Power of two, but > 65536
            // The arena ends right after the would-be 32 MiB block: without the range check the walk takes
            // that block, which covers buf2, and buf2_good_rec is lost. With it, buf1 is one bad region and
            // the zeros after buf2 up to arenaUsed are a second one.
            image.setArenaUsed(detail::kArenaOffset + sizeof(detail::BufferHeaderDisk) +
                               std::uint64_t{131072} * detail::kSlotBytes);
            expectedSkippedBuffers = 2;
            expectedUndeliveredLines = 1; // Only buf2 recovered
            break;
        }
        case CorruptionType::WritePosLessThanReadPos: {
            SCOPED_TRACE("WritePosLessThanReadPos");
            ASSERT_TRUE(buf1->tryWrite(kTestSteadyBaseNs + 100, 0, 1, Level::Info, "buf1_rec"));
            auto* diskHdr = reinterpret_cast<detail::BufferHeaderDisk*>(image.data() + detail::kArenaOffset);
            diskHdr->writePos = 1;
            diskHdr->readPos = 2; // writePos < readPos
            expectedSkippedBuffers = 1;
            expectedUndeliveredLines = 1; // Only buf2 recovered
            break;
        }
        case CorruptionType::LenGreaterThan232: {
            SCOPED_TRACE("LenGreaterThan232");
            ASSERT_TRUE(buf1->tryWrite(kTestSteadyBaseNs + 100, 0, 1, Level::Info, "buf1_rec1_good"));
            ASSERT_TRUE(buf1->tryWrite(kTestSteadyBaseNs + 150, 1, 1, Level::Info, "buf1_rec2_bad_len"));
            std::byte* slot1 = image.data() + detail::kArenaOffset + sizeof(detail::BufferHeaderDisk) + detail::kSlotBytes;
            auto* slotHdr = reinterpret_cast<detail::SlotHeader*>(slot1);
            slotHdr->len = 250; // > 232: record skipped per Plan D4 step 7
            expectedSkippedBuffers = 0;
            expectedUndeliveredLines = 2; // buf1_rec1_good + buf2_good_rec
            break;
        }
        case CorruptionType::BrokenContinuation: {
            SCOPED_TRACE("BrokenContinuation");
            ASSERT_TRUE(buf1->tryWrite(kTestSteadyBaseNs + 100, 0, 1, Level::Info, "buf1_rec1_good"));
            ASSERT_TRUE(buf1->tryWrite(kTestSteadyBaseNs + 150, 1, 1, Level::Info, "buf1_rec2_broken"));
            ASSERT_TRUE(buf1->tryWrite(kTestSteadyBaseNs + 180, 2, 1, Level::Info, "buf1_rec3_good"));
            // Break continuation on rec2: clear Last flag so it has First flag without Last before next First
            std::byte* slot1 = image.data() + detail::kArenaOffset + sizeof(detail::BufferHeaderDisk) + detail::kSlotBytes;
            auto* slotHdr = reinterpret_cast<detail::SlotHeader*>(slot1);
            slotHdr->flags = detail::kSlotFlagFirst;
            expectedSkippedBuffers = 0;
            expectedUndeliveredLines = 3; // buf1_rec1_good + buf1_rec3_good + buf2_good_rec
            break;
        }
        }

        image.writeTo(testDir_);

        auto res = recoverLogMaps(testDir_);
        ASSERT_TRUE(res.has_value());
        ASSERT_EQ(res.value().size(), 1u);

        const LogMapRecovery& rec = res.value()[0];
        EXPECT_EQ(rec.skippedBuffers, expectedSkippedBuffers);
        EXPECT_EQ(rec.undeliveredLines, expectedUndeliveredLines);

        const std::string text = readFileText(rec.recoveredFile);
        EXPECT_NE(text.find("buf2_good_rec"), std::string::npos);
        if (corruption == CorruptionType::LenGreaterThan232) {
            EXPECT_NE(text.find("buf1_rec1_good"), std::string::npos);
            EXPECT_EQ(text.find("buf1_rec2_bad_len"), std::string::npos);
        } else if (corruption == CorruptionType::BrokenContinuation) {
            EXPECT_NE(text.find("buf1_rec1_good"), std::string::npos);
            EXPECT_NE(text.find("buf1_rec3_good"), std::string::npos);
            EXPECT_EQ(text.find("buf1_rec2_broken"), std::string::npos);
        }
    }
}

TEST_F(LogMapRecoveryTest, LongRecordAcrossSlots) {
    MapImage image;
    image.setLabel(1, "app.log");
    auto* buf = image.addBuffer(64, 1);
    ASSERT_NE(buf, nullptr);

    const std::string longText(500, 'K');
    ASSERT_TRUE(buf->tryWrite(kTestSteadyBaseNs + 100, 0, 1, Level::Info, longText));

    image.writeTo(testDir_);

    auto res = recoverLogMaps(testDir_);
    ASSERT_TRUE(res.has_value());
    ASSERT_EQ(res.value().size(), 1u);
    EXPECT_EQ(res.value()[0].undeliveredLines, 1u);

    const std::string text = readFileText(res.value()[0].recoveredFile);
    EXPECT_NE(text.find(longText), std::string::npos);
}

TEST_F(LogMapRecoveryTest, MutationsNeverCrash) {
    MapImage baseImage(128 * 1024);
    baseImage.setLabel(1, "app.log");
    auto* b1 = baseImage.addBuffer(64, 1);
    ASSERT_NE(b1, nullptr);
    ASSERT_TRUE(b1->tryWrite(kTestSteadyBaseNs + 10, 0, 1, Level::Info, "base_msg1"));
    auto* b2 = baseImage.addBuffer(64, 2);
    ASSERT_NE(b2, nullptr);
    ASSERT_TRUE(b2->tryWrite(kTestSteadyBaseNs + 20, 0, 1, Level::Warn, "base_msg2"));
    baseImage.syncHeader();

    const std::size_t baseSize = baseImage.size();
    const std::byte* baseData = baseImage.data();

    std::mt19937_64 rng(12345);
    std::uniform_int_distribution<int> kindDist(0, 3);
    std::uniform_int_distribution<int> flipCountDist(1, 16);
    std::uniform_int_distribution<unsigned int> byteDist(0, 255);

    for (int iter = 0; iter < 1000; ++iter) {
        std::vector<std::byte> buf(baseData, baseData + baseSize);
        const int kind = kindDist(rng);
        if (kind == 0) {
            // flip 1..16 random bytes anywhere
            const int flips = flipCountDist(rng);
            std::uniform_int_distribution<std::size_t> posDist(0, buf.size() - 1);
            for (int f = 0; f < flips; ++f) {
                const std::size_t p = posDist(rng);
                buf[p] ^= static_cast<std::byte>(byteDist(rng) | 1u);
            }
        } else if (kind == 1) {
            // truncate to a random length; keep the header valid (set fileBytes to new length, arenaUsed as is)
            std::uniform_int_distribution<std::size_t> lenDist(0, buf.size());
            const std::size_t len = lenDist(rng);
            buf.resize(len);
            if (len >= sizeof(detail::MapHeader)) {
                auto* hdr = reinterpret_cast<detail::MapHeader*>(buf.data());
                hdr->fileBytes = static_cast<std::uint64_t>(len);
            }
        } else if (kind == 2) {
            // random bytes of random length
            std::uniform_int_distribution<std::size_t> lenDist(0, buf.size());
            const std::size_t len = lenDist(rng);
            buf.resize(len);
            for (std::size_t i = 0; i < len; ++i) {
                buf[i] = static_cast<std::byte>(byteDist(rng));
            }
        } else {
            // randomize bytes in the arena only under a valid header
            std::uniform_int_distribution<std::size_t> arenaPosDist(detail::kArenaOffset, buf.size() - 1);
            std::uniform_int_distribution<std::size_t> countDist(1, buf.size() - detail::kArenaOffset);
            const std::size_t count = countDist(rng);
            for (std::size_t c = 0; c < count; ++c) {
                const std::size_t p = arenaPosDist(rng);
                buf[p] = static_cast<std::byte>(byteDist(rng));
            }
        }

        const fs::path filePath = testDir_ / kTestMapFileName;
        {
            std::ofstream out(filePath, std::ios::binary);
            if (!buf.empty()) {
                out.write(reinterpret_cast<const char*>(buf.data()), static_cast<std::streamsize>(buf.size()));
            }
        }

        auto res = recoverLogMaps(testDir_);
        ASSERT_TRUE(res.has_value());

        std::error_code ec;
        for (const auto& entry : fs::directory_iterator(testDir_, ec)) {
            fs::remove_all(entry.path(), ec);
        }
    }
}

TEST_F(LogMapRecoveryTest, MissingDirectoryReturnsEmpty) {
    const fs::path missing = testDir_ / "missing_subdir";
    auto res = recoverLogMaps(missing);
    ASSERT_TRUE(res.has_value());
    EXPECT_TRUE(res.value().empty());
}
