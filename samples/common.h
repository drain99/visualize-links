#include <array>

using std::size_t;

template <typename T, size_t N> std::array<T *, N> nodes() {
  std::array<T *, N> ret;
  for (int i = 0; i < N; ++i) {
    ret[i] = new T(i);
  }
  return ret;
}
