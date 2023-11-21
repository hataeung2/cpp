#ifndef __ATIME__
#define __ATIME__
import <string>;
import <sstream>;
import <chrono>;
import <time.h>;

using namespace std;
namespace alog {
class TimeStamp {
public:
  enum OPTION : unsigned int {
    eNothing = 0x0000,
    eWithFmt = 0x0001,
    eAddSpace = 0x0002,
  };
  using OptFlags = unsigned int;
public:
  static const string str(const OptFlags opt = eWithFmt | eAddSpace) {
      namespace time = std::chrono;
      // if no problem at ostream add here with timestamp
      auto currentTime = time::system_clock::now();
      auto timeFmt = time::system_clock::to_time_t(currentTime);
      auto milliseconds = time::duration_cast<time::milliseconds>(currentTime.time_since_epoch() % time::seconds(1));
      struct tm localTime;
      #ifdef _WIN32
      _localtime64_s(&localTime, &timeFmt);
      #else
      localtime_s(&localTime, &timeFmt);
      #endif
      std::ostringstream oss;
      if (opt & eWithFmt) {
        oss << std::put_time(&localTime, "%Y-%m-%d %H:%M:%S.");
      } else {
        oss << std::put_time(&localTime, "%Y%m%d%H%M%S");
      } 
      oss << std::setw(3) << std::setfill('0') << milliseconds.count();
      if (opt & eAddSpace) {
        oss << " ";
      }
      return oss.str();
  }
};

}//!namespace alog {

#endif//!__ATIME__