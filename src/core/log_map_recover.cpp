#include <algorithm>
#include <chrono>
#include <bit>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <format>
#include <fstream>
#include <limits>
#include <new>
#include <optional>
#include <string>
#include <string_view>
#include <system_error>
#include <thread>
#include <utility>
#include <vector>

#include "atugcc/core/detail/log_map.hpp"
#include "atugcc/core/detail/thread_log_buffer.hpp"
#include "atugcc/core/log_buffer_config.hpp"
#include "mapped_file.hpp"

namespace atugcc::core {

namespace {

constexpr int kLockRetries = 20;                               // 20 x 50 ms
constexpr auto kLockRetryInterval = std::chrono::milliseconds(50);

// The pid in a map's header, read without the lock (0 when the header cannot be read).
std::uint32_t headerPid(const std::filesystem::path& path) noexcept {
    try {
        std::ifstream in(path, std::ios::binary);
        detail::MapHeader header{};
        if (!in.read(reinterpret_cast<char*>(&header), sizeof header)) {
            return 0;
        }
        if (std::memcmp(header.magic, detail::kMapMagic.data(), detail::kMapMagicBytes) != 0) {
            return 0;
        }
        return header.pid;
    } catch (...) {  // unreadable header: treat the owner as unknown, which skips the wait
        return 0;
    }
}

// openIfEnded, but when the lock is held by a process that no longer exists, wait for the OS to
// release it: on Linux a SIGKILLed multi-threaded owner can hold its flock for a short time after
// its parent's wait() returns (measured 2026-10-30, under 200 ms), and a supervisor may restart the
// program within that time. A live owner is skipped at once.
Expected<std::optional<detail::MappedFile>> openEndedOrWait(const std::filesystem::path& path) {
    auto res = detail::MappedFile::openIfEnded(path);
    if (!res.has_value() || res->has_value()) {
        return res;
    }
    const std::uint32_t pid = headerPid(path);
    if (pid == 0 || pid == detail::MappedFile::currentProcessId() || detail::MappedFile::processAlive(pid)) {
        return res;
    }
    for (int i = 0; i < kLockRetries; ++i) {
        std::this_thread::sleep_for(kLockRetryInterval);
        res = detail::MappedFile::openIfEnded(path);
        if (!res.has_value() || res->has_value()) {
            return res;
        }
    }
    const std::string msg = std::format("[atugcc] {} is still locked although pid {} ended: skipped (a later run recovers it)\n",
                                        path.filename().string(), pid);
    std::fputs(msg.c_str(), stderr);
    return res;
}

struct RecoveredRecord {
    std::uint64_t time_ns_{0};
    std::uint32_t thread_no_{0};
    std::uint32_t thread_seq_{0};
    std::uint16_t logger_id_{0};
    bool is_undelivered_{false};
    std::string text_{};
};

bool readHeader(const detail::MappedFile& mapped, detail::MapHeader& outHeader) noexcept {
    const std::size_t size = mapped.size();
    if (size < detail::kArenaOffset) {
        return false;
    }
    std::memcpy(&outHeader, mapped.data(), sizeof(outHeader));
    if (std::memcmp(outHeader.magic, detail::kMapMagic.data(), detail::kMapMagic.size()) != 0) {
        return false;
    }
    if (outHeader.version != detail::kMapVersion) {
        return false;
    }
    if (outHeader.arenaOffset != detail::kArenaOffset) {
        return false;
    }
    if (outHeader.fileBytes != static_cast<std::uint64_t>(size)) {
        return false;
    }
    if (outHeader.labelCount != detail::kLabelCount) {
        return false;
    }
    if (outHeader.labelBytes != detail::kLabelBytes) {
        return false;
    }
    return true;
}

std::vector<std::string> readLabels(const detail::MappedFile& mapped) {
    std::vector<std::string> labels;
    labels.reserve(detail::kLabelCount);

    const std::byte* data = mapped.data();
    for (std::uint32_t i = 0; i < detail::kLabelCount; ++i) {
        if (i == 0) {
            labels.emplace_back("dbgbuf");
            continue;
        }
        const std::size_t offset = detail::kLabelTableOffset + static_cast<std::size_t>(i) * sizeof(detail::LabelEntry);
        detail::LabelEntry entry{};
        std::memcpy(&entry, data + offset, sizeof(entry));

        if (entry.id == static_cast<std::uint16_t>(i) &&
            entry.len <= detail::kLabelTextBytes &&
            entry.len > 0) {
            labels.emplace_back(entry.text, static_cast<std::size_t>(entry.len));
        } else {
            labels.push_back(std::format("logger#{}", i));
        }
    }
    return labels;
}

std::string formatLabel(std::uint16_t loggerId, const std::vector<std::string>& labels) {
    if (loggerId == 0) {
        return "dbgbuf";
    }
    if (static_cast<std::size_t>(loggerId) < labels.size()) {
        return labels[loggerId];
    }
    return std::format("logger#{}", loggerId);
}

bool isBufferHeaderValid(const std::byte* data,
                         std::uint64_t offset,
                         std::uint64_t end,
                         std::uint64_t fileSize,
                         detail::BufferHeaderDisk& outHeader,
                         std::uint64_t& outBlockSize) noexcept {
    if (offset > end || sizeof(detail::BufferHeaderDisk) > end - offset) {
        return false;
    }
    if (offset > fileSize || sizeof(detail::BufferHeaderDisk) > fileSize - offset) {
        return false;
    }

    std::memcpy(&outHeader, data + offset, sizeof(outHeader));

    if (std::memcmp(outHeader.magic, detail::kMagic.data(), detail::kMagic.size()) != 0) {
        return false;
    }
    if (outHeader.slotBytes != detail::kSlotBytes) {
        return false;
    }
    if (outHeader.slotCount < detail::kMinSlots ||
        outHeader.slotCount > detail::kMaxSlots ||
        (outHeader.slotCount & (outHeader.slotCount - 1u)) != 0) {
        return false;
    }

    const std::uint64_t slotsBytes = static_cast<std::uint64_t>(outHeader.slotCount) * detail::kSlotBytes;
    const std::uint64_t blockSize = sizeof(detail::BufferHeaderDisk) + slotsBytes;
    outBlockSize = blockSize;

    if (blockSize > end || offset > end - blockSize) {
        return false;
    }
    if (blockSize > fileSize || offset > fileSize - blockSize) {
        return false;
    }

    if (outHeader.readPos > outHeader.writePos || outHeader.writePos > outHeader.reservePos) {
        return false;
    }
    if (outHeader.writePos - outHeader.readPos > static_cast<std::uint64_t>(outHeader.slotCount)) {
        return false;
    }

    return true;
}

void collectBufferRecords(const std::byte* data,
                          std::uint64_t bufOffset,
                          const detail::BufferHeaderDisk& bufHeader,
                          std::uint64_t fileSize,
                          std::vector<RecoveredRecord>& outRecords,
                          std::uint64_t& outUndeliveredCount,
                          std::uint64_t& outDeliveredCount) {
    const std::uint64_t maxReserveWrite = std::max(bufHeader.reservePos, bufHeader.writePos);
    const std::uint64_t slotCount64 = static_cast<std::uint64_t>(bufHeader.slotCount);
    const std::uint64_t startPos = (maxReserveWrite > slotCount64) ? (maxReserveWrite - slotCount64) : 0ULL;
    const std::uint64_t endPos = bufHeader.writePos;
    if (startPos >= endPos) {
        return;
    }

    const std::uint32_t mask = bufHeader.slotCount - 1u;
    const std::uint64_t maxSlotsPerRecord = static_cast<std::uint64_t>(bufHeader.slotCount / 2u);

    std::uint64_t pos = startPos;
    while (pos < endPos) {
        const std::uint32_t firstIdx = static_cast<std::uint32_t>(pos & mask);
        const std::uint64_t firstSlotOffset = bufOffset + sizeof(detail::BufferHeaderDisk) +
            static_cast<std::uint64_t>(firstIdx) * detail::kSlotBytes;

        if (firstSlotOffset > fileSize || detail::kSlotBytes > fileSize - firstSlotOffset) {
            ++pos;
            continue;
        }

        detail::SlotHeader firstHdr{};
        std::memcpy(&firstHdr, data + firstSlotOffset, sizeof(firstHdr));

        if ((firstHdr.flags & detail::kSlotFlagFirst) == 0 || firstHdr.len > detail::kSlotPayloadBytes) {
            ++pos;
            continue;
        }

        bool complete = false;
        std::uint64_t recordEnd = pos;
        const std::uint64_t maxCheckEnd = (endPos - pos > maxSlotsPerRecord) ? pos + maxSlotsPerRecord : endPos;  // pos < endPos: no wrap

        for (std::uint64_t cur = pos; cur < maxCheckEnd; ++cur) {
            const std::uint32_t curIdx = static_cast<std::uint32_t>(cur & mask);
            const std::uint64_t curSlotOffset = bufOffset + sizeof(detail::BufferHeaderDisk) +
                static_cast<std::uint64_t>(curIdx) * detail::kSlotBytes;

            if (curSlotOffset > fileSize || detail::kSlotBytes > fileSize - curSlotOffset) {
                break;
            }

            detail::SlotHeader curHdr{};
            std::memcpy(&curHdr, data + curSlotOffset, sizeof(curHdr));

            if (curHdr.len > detail::kSlotPayloadBytes) {
                break;
            }

            if (cur > pos) {
                if ((curHdr.flags & detail::kSlotFlagFirst) != 0 ||
                    curHdr.timeNs != firstHdr.timeNs ||
                    curHdr.threadSeq != firstHdr.threadSeq ||
                    curHdr.loggerId != firstHdr.loggerId) {
                    break;
                }
            }

            if ((curHdr.flags & detail::kSlotFlagLast) != 0) {
                complete = true;
                recordEnd = cur;
                break;
            }
        }

        if (!complete) {
            ++pos;
            continue;
        }

        std::string recordText;
        for (std::uint64_t cur = pos; cur <= recordEnd; ++cur) {
            const std::uint32_t curIdx = static_cast<std::uint32_t>(cur & mask);
            const std::uint64_t curSlotOffset = bufOffset + sizeof(detail::BufferHeaderDisk) +
                static_cast<std::uint64_t>(curIdx) * detail::kSlotBytes;

            detail::SlotHeader curHdr{};
            std::memcpy(&curHdr, data + curSlotOffset, sizeof(curHdr));

            const std::size_t chunkLen = std::min(static_cast<std::size_t>(curHdr.len),
                                                  static_cast<std::size_t>(detail::kSlotPayloadBytes));
            const std::uint64_t payloadOffset = curSlotOffset + sizeof(detail::SlotHeader);
            if (chunkLen > 0 && payloadOffset <= fileSize && chunkLen <= fileSize - payloadOffset) {
                const std::size_t oldSize = recordText.size();
                recordText.resize(oldSize + chunkLen);
                std::memcpy(recordText.data() + oldSize, data + payloadOffset, chunkLen);
            }
        }

        for (char& ch : recordText) {
            if (ch == '\n' || ch == '\r') {
                ch = ' ';
            }
        }

        const bool isUndelivered = (recordEnd + 1ULL > bufHeader.readPos);
        if (isUndelivered) {
            ++outUndeliveredCount;
        } else {
            ++outDeliveredCount;
        }

        outRecords.push_back(RecoveredRecord{
            .time_ns_ = firstHdr.timeNs,
            .thread_no_ = bufHeader.threadNo,
            .thread_seq_ = firstHdr.threadSeq,
            .logger_id_ = firstHdr.loggerId,
            .is_undelivered_ = isUndelivered,
            .text_ = std::move(recordText)
        });

        pos = recordEnd + 1ULL;
    }
}

void walkArena(const detail::MappedFile& mapped,
               const detail::MapHeader& header,
               std::vector<RecoveredRecord>& outRecords,
               std::uint64_t& outUndeliveredCount,
               std::uint64_t& outDeliveredCount,
               std::uint32_t& outSkippedBuffers) {
    const std::uint64_t fileSize = mapped.size();
    std::uint64_t end = fileSize;
    if (header.arenaUsed >= detail::kArenaOffset && header.arenaUsed <= fileSize) {
        end = header.arenaUsed;
    }

    const std::byte* data = mapped.data();
    std::uint64_t offset = detail::kArenaOffset;

    while (offset < end) {
        detail::BufferHeaderDisk bufHeader{};
        std::uint64_t blockSize = 0;
        if (isBufferHeaderValid(data, offset, end, fileSize, bufHeader, blockSize)) {
            collectBufferRecords(data, offset, bufHeader, fileSize, outRecords, outUndeliveredCount, outDeliveredCount);
            offset += blockSize;
        } else {
            ++outSkippedBuffers;
            offset += 64ULL;
            while (offset < end) {
                detail::BufferHeaderDisk nextHeader{};
                std::uint64_t nextBlockSize = 0;
                if (isBufferHeaderValid(data, offset, end, fileSize, nextHeader, nextBlockSize)) {
                    break;
                }
                offset += 64ULL;
            }
        }
    }
}

constexpr std::uint64_t kMaxValidNs = static_cast<std::uint64_t>(std::numeric_limits<std::int64_t>::max());

bool isValidSystemNs(std::uint64_t ns) noexcept {
    return ns <= kMaxValidNs;
}

std::optional<std::int64_t> computeWallTimeNs(std::uint64_t timeNs,
                                              std::uint64_t steadyBaseNs,
                                              std::int64_t systemBaseNs) noexcept {
    if (timeNs >= steadyBaseNs) {
        const std::uint64_t diff = timeNs - steadyBaseNs;
        if (systemBaseNs >= 0) {
            const std::uint64_t sys = static_cast<std::uint64_t>(systemBaseNs);
            if (diff > kMaxValidNs - sys) {
                return std::nullopt;
            }
            const std::uint64_t res = sys + diff;
            return static_cast<std::int64_t>(res);
        } else {
            const std::uint64_t absSys = (systemBaseNs == std::numeric_limits<std::int64_t>::min())
                ? (static_cast<std::uint64_t>(std::numeric_limits<std::int64_t>::max()) + 1ULL)
                : static_cast<std::uint64_t>(-systemBaseNs);
            if (diff < absSys) {
                return std::nullopt;
            }
            const std::uint64_t res = diff - absSys;
            if (res > kMaxValidNs) {
                return std::nullopt;
            }
            return static_cast<std::int64_t>(res);
        }
    } else {
        const std::uint64_t diff = steadyBaseNs - timeNs;
        if (systemBaseNs < 0) {
            return std::nullopt;
        }
        const std::uint64_t sys = static_cast<std::uint64_t>(systemBaseNs);
        if (sys < diff) {
            return std::nullopt;
        }
        const std::uint64_t res = sys - diff;
        return static_cast<std::int64_t>(res);
    }
}

bool writeRecoveredFile(const std::filesystem::path& dir,
                        const std::string& mapFileName,
                        const detail::MapHeader& header,
                        const std::vector<std::string>& labels,
                        const std::vector<RecoveredRecord>& records,
                        std::uint64_t undeliveredCount,
                        std::uint64_t deliveredCount,
                        std::uint32_t skippedBuffers,
                        std::filesystem::path& outFinalPath) {
    const bool startValid = isValidSystemNs(header.startSystemNs);
    const std::string startCompact = startValid
        ? detail::formatCompactUtc(static_cast<std::int64_t>(header.startSystemNs))
        : std::string("00000000T000000000");
    const std::string finalFileName = std::format("recovered_{}_{}.log", startCompact, header.pid);
    const std::filesystem::path finalPath = dir / finalFileName;
    const std::filesystem::path tmpPath = dir / (finalFileName + ".tmp");

    {
        std::ofstream out(tmpPath, std::ios::binary);
        if (!out) {
            return false;
        }

        const std::string wallStart = startValid
            ? detail::formatIsoUtcMicros(static_cast<std::int64_t>(header.startSystemNs))
            : std::string("invalid-time");
        const char* crashStr = ((header.flags & detail::kMapFlagCrash) != 0) ? "yes" : "no";

        out << "# atugcc recovered log (spec 010-10)\n";
        out << std::format("# pid {}, started {}, map {}\n", header.pid, wallStart, mapFileName);
        out << std::format("# ended without a clean exit; crash handler: {}\n", crashStr);
        out << std::format("# {} undelivered lines (never reached any sink: not in the log file), {} delivered lines (context), {} skipped buffers\n",
                           undeliveredCount, deliveredCount, skippedBuffers);
        out << "# a line delivered just before the end can appear both here as undelivered and in the log file\n";

        for (const auto& rec : records) {
            const auto wallNsOpt = computeWallTimeNs(rec.time_ns_, header.steadyBaseNs, header.systemBaseNs);
            const std::string wall = wallNsOpt.has_value()
                ? detail::formatIsoUtcMicros(*wallNsOpt)
                : std::string("invalid-time");
            const char* status = rec.is_undelivered_ ? "undelivered" : "delivered";
            const std::string label = formatLabel(rec.logger_id_, labels);
            out << std::format("{} T{} [{}] {} {}\n", wall, rec.thread_no_, status, label, rec.text_);
        }

        out.close();
        if (!out) {
            std::error_code removeEc;
            std::filesystem::remove(tmpPath, removeEc);
            return false;
        }
    }

    std::error_code ec;
    std::filesystem::remove(finalPath, ec);
    std::filesystem::rename(tmpPath, finalPath, ec);
    if (ec) {
        std::error_code removeEc;
        std::filesystem::remove(tmpPath, removeEc);
        return false;
    }

    outFinalPath = finalPath;
    return true;
}

} // namespace

Expected<std::vector<LogMapRecovery>> recoverLogMaps(const std::filesystem::path& dir) {
    try {
        std::error_code ec;
        const bool exists = std::filesystem::exists(dir, ec);
        if (!exists && !ec) {
            return std::vector<LogMapRecovery>{};
        }
        if (ec) {
            if (ec == std::errc::no_such_file_or_directory) {
                return std::vector<LogMapRecovery>{};
            }
            return std::unexpected(CoreError::FileIOFailure);
        }

        const bool isDir = std::filesystem::is_directory(dir, ec);
        if (ec || !isDir) {
            return std::unexpected(CoreError::FileIOFailure);
        }

        std::vector<std::filesystem::path> mapFiles;
        for (auto it = std::filesystem::directory_iterator(dir, ec);
             !ec && it != std::filesystem::directory_iterator();
             it.increment(ec)) {
            if (it->path().extension() == ".logmap") {
                mapFiles.push_back(it->path());
            }
        }
        if (ec) {
            return std::unexpected(CoreError::FileIOFailure);
        }

        std::sort(mapFiles.begin(), mapFiles.end(), [](const std::filesystem::path& a, const std::filesystem::path& b) {
            return a.filename() < b.filename();
        });

        std::vector<LogMapRecovery> recoveries;

        for (const auto& path : mapFiles) {
            const std::string name = path.filename().string();
            auto openRes = openEndedOrWait(path);
            if (!openRes.has_value()) {
                const std::string msg = std::format("[atugcc] cannot open {}: skipped\n", name);
                std::fputs(msg.c_str(), stderr);
                continue;
            }
            if (!openRes.value().has_value()) {
                continue;
            }

            std::optional<detail::MappedFile> mappedFile(std::move(*openRes.value()));

            detail::MapHeader header{};
            if (!readHeader(*mappedFile, header)) {
                mappedFile.reset();
                std::filesystem::path corruptPath = path;
                corruptPath += ".corrupt";
                std::filesystem::remove(corruptPath, ec);
                std::filesystem::rename(path, corruptPath, ec);
                const std::string msg = std::format("[atugcc] {} is not a readable log map: renamed to {}.corrupt\n", name, name);
                std::fputs(msg.c_str(), stderr);
                continue;
            }

            if ((header.flags & detail::kMapFlagCleanExit) != 0) {
                if (!mappedFile->removeFile().has_value()) {
                    const std::string msg = std::format("[atugcc] cannot remove {} (clean exit): skipped\n", name);
                    std::fputs(msg.c_str(), stderr);
                }
                mappedFile.reset();
                continue;
            }

            const std::vector<std::string> labels = readLabels(*mappedFile);

            std::vector<RecoveredRecord> records;
            std::uint64_t undeliveredCount = 0;
            std::uint64_t deliveredCount = 0;
            std::uint32_t skippedBuffers = 0;

            walkArena(*mappedFile, header, records, undeliveredCount, deliveredCount, skippedBuffers);

            std::sort(records.begin(), records.end(), [](const RecoveredRecord& a, const RecoveredRecord& b) noexcept {
                if (a.time_ns_ != b.time_ns_) {
                    return a.time_ns_ < b.time_ns_;
                }
                if (a.thread_no_ != b.thread_no_) {
                    return a.thread_no_ < b.thread_no_;
                }
                return a.thread_seq_ < b.thread_seq_;
            });

            std::filesystem::path finalPath;
            if (!writeRecoveredFile(dir, name, header, labels, records, undeliveredCount, deliveredCount, skippedBuffers, finalPath)) {
                mappedFile.reset();
                const std::string msg = std::format("[atugcc] cannot write {}: skipped\n", name);
                std::fputs(msg.c_str(), stderr);
                continue;
            }

            const auto removeRes = mappedFile->removeFile();
            mappedFile.reset();

            if (removeRes.has_value()) {
                const std::string successMsg = std::format("[atugcc] recovered {} undelivered lines from pid {} into {}\n",
                                                           undeliveredCount, header.pid, finalPath.string());
                std::fputs(successMsg.c_str(), stderr);
            } else {
                const std::string warnMsg = std::format(
                    "[atugcc] recovered {} undelivered lines from pid {} into {}, but cannot remove {}: it will be recovered again\n",
                    undeliveredCount, header.pid, finalPath.string(), name);
                std::fputs(warnMsg.c_str(), stderr);
            }

            recoveries.push_back(LogMapRecovery{
                .recoveredFile = std::move(finalPath),
                .pid = header.pid,
                .undeliveredLines = undeliveredCount,
                .deliveredLines = deliveredCount,
                .skippedBuffers = skippedBuffers,
                .crashHandlerRan = ((header.flags & detail::kMapFlagCrash) != 0)
            });
        }

        return recoveries;
    } catch (const std::bad_alloc&) {
        return std::unexpected(CoreError::Unexpected);
    } catch (...) {
        return std::unexpected(CoreError::Unexpected);
    }
}

} // namespace atugcc::core
