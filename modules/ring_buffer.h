/**
 * @file ring_buffer.h
 * @author Taeung Ha (aha3546@outlook.com) referenced from the book named C++20 for expert
 * @brief thread safe memory buffer to store string type data. e.g. log
 * 
 * @version 0.1
 * @date 2023-11-17
 * 
 * @copyright Copyright (c) 2023
 * 
 */

#ifndef __RING_BUFFER__
#define __RING_BUFFER__
#ifdef _WIN32
import <sstream>;
import <vector>;
import <mutex>;
import <chrono>;
#else
#include <sstream>
#include <vector>
#include <mutex>
#include <chrono>
#endif
using namespace std;

namespace alog {

class RingBuffer {
public:
  explicit RingBuffer(size_t numEntries = DefaultNumEntries, std::ostream* ostr = nullptr);
  virtual ~RingBuffer() = default;

  template <typename... Args>
  inline void addEntry(const Args&... args)
  {
    std::ostringstream os;
    ((os << args), ...); // folding expr.
    addStringEntry(os.str());
  }

  /**
   * @brief helper for send out the entries to ostr
   * 
   * @param ostr. output stream
   * @param rb. ring buffer with max elem of DefaultNumEntries
   * @return std::ostream& 
   */
  friend std::ostream& operator<<(std::ostream& ostr, RingBuffer& rb);

  /**
   * @brief Set the Target Output stream
   * 
   * @param newOstr to be new target. m_ostr is going to be changed with newOstr
   * @return std::ostream* 
   */
  std::ostream* setOutput(std::ostream* newOstr);

private:
  std::vector<std::string> m_entries;
  std::vector<std::string>::iterator m_next;
  std::ostream* m_ostr { nullptr };
  bool m_wrapped { false };
  std::mutex m_mutex;

  static const size_t DefaultNumEntries{ 256 };

  /**
   * @brief add an entry into m_entries
   * 
   * @param entry 
   */
  void addStringEntry(std::string&& entry);
};



class DbgBuf {
public:
  template<typename... Args>
  static void log(const Args&... args) {
    m_buf.addEntry(args...);
  }
  static alog::RingBuffer& get() { return m_buf; }
private:
  static alog::RingBuffer m_buf;
};



}//!namespace alog {
#endif//!__RING_BUFFER__