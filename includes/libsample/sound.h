#ifndef __SOUND__
#define __SOUND__

#if defined(_WIN32)
  #ifdef SOUND_EXPORTS
  #define SOUND_DECL __declspec(dllexport)
  #define SOUND_DECL_EXTERN
  #else
  #define SOUND_DECL __declspec(dllimport)
  #define SOUND_DECL_EXTERN extern
  #endif
#else
  #define SOUND_DECL
#endif

class SOUND_DECL Sound {
 public:
  Sound(int volume);
  int MakeNoize() const;
 private:
  int volume_;
};

#endif//!__SOUND__