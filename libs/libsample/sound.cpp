#include "sound.h"

Sound::Sound(int volume) : volume_(volume) {}

int Sound::MakeNoize() const {
  return volume_;
}
