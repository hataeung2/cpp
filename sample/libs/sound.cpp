#include "sound.h"

namespace sample {

Sound::Sound(int volume) : volume_(volume) {}

int Sound::makeNoise() const {
  return volume_;
}

}  // namespace sample
