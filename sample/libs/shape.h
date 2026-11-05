#ifndef __SHAPE__
#define __SHAPE__

// namespace: <Windows.h> declares a global Rectangle() function
namespace sample {

class Rectangle {
 public:
  Rectangle(int width, int height);
  int getSize() const;
 private:
  int width_, height_;
};

}  // namespace sample

#endif//!__SHAPE__