#ifndef __SHAPE__
#define __SHAPE__

class Rectangle {
 public:
  Rectangle(int width, int height);
  int GetSize() const;
 private:
  int width_, height_;
};

#endif//!__SHAPE__