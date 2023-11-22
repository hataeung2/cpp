#include "shape.h"
#include <fmt/core.h> 

Rectangle::Rectangle(int width, int height) : width_(width), height_(height) {}

int Rectangle::GetSize() const {
  fmt::print("width : {} \n", width_ * height_);
  return width_ * height_;
}