// Copyright (c) Indrajit Banerjee
// Licensed under the MIT License.

#include <array>

using std::size_t;

template <typename T, size_t N> std::array<T *, N> nodes() {
  std::array<T *, N> ret;
  for (int i = 0; i < N; ++i) {
    ret[i] = new T(i);
  }
  return ret;
}

struct ListNode {
  int val;
  ListNode *next = nullptr;

  ListNode() : val(0) {}
  ListNode(int val) : val(val) {}
};
