#include "ring_buffer.h"
#include "atime.hpp"
#include <iterator>
#include <utility>

alog::RingBuffer alog::DbgBuf::m_buf;

namespace alog {

RingBuffer::RingBuffer(size_t numEntries /*= DefaultNumEntries*/, ostream* ostr /*= nullptr*/)
  : m_entries{numEntries}, m_ostr{ostr}, m_wrapped{false}
{
  if (0 == numEntries) {
    throw invalid_argument{ "Number of entries must be > 0." };
  }
  // set target position to add
  m_next = begin(m_entries);
}

void RingBuffer::addStringEntry(string&& entry) 
{
  lock_guard<mutex> lock(m_mutex);
  using tstmp = TimeStamp;
  entry = tstmp::str(tstmp::OPTION::eWithFmt | tstmp::OPTION::eAddSpace) + entry;
  if (m_ostr) { 
    *m_ostr 
    << entry 
    << endl; 
  }
  // then move the target to the position which is being pointed
  *m_next = move(entry);
  // then point the target to vacant position
  ++m_next;

  // get the target back to the first position if it reached end of the buffer
  if (end(m_entries) == m_next) {
    m_next = begin(m_entries);
    m_wrapped = true;
  }
}

/**
  * @brief m_ostr is to be replaced with newOstr and return the last m_ostr
  * 
  * @return return (last m_ostr. which is the one before replacement)
  */
ostream* RingBuffer::setOutput(ostream* newOstr)
{
  return exchange(m_ostr, newOstr);
}

ostream& operator<<(ostream& ostr, RingBuffer& rb)
{
  if (rb.m_wrapped) {
    copy(rb.m_next, end(rb.m_entries), ostream_iterator<string>{ostr, "\n"});
  }

  copy(begin(rb.m_entries), rb.m_next, ostream_iterator<string>{ostr, "\n"});

  return ostr;
}

}//!namespace alog {