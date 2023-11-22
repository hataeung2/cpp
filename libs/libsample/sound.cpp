#include "sound.h"
#include <fmt/core.h>

Sound::Sound(int volume) : volume_(volume) {}

int Sound::MakeNoize() const {
  fmt::print("Noize Volume : {} \n", volume_);
  return volume_;
}
