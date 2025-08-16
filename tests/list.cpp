#include "common.h"

ListNode *list_linear1() {
  auto [x, y, z] = nodes<ListNode, 3>();
  x->next = y;
  y->next = z;
  return x;
}

ListNode *list_cyclic1() {
  auto [x, y, z] = nodes<ListNode, 3>();
  x->next = y;
  y->next = z;
  z->next = x;
  return x;
}

template <size_t N> ListNode *list_linear2() {
  auto allNodes = nodes<ListNode, N>();
  for (size_t i = 0; i < N; ++i) {
    allNodes[i]->val = i;
  }
  for (size_t i = 0; i + 1 < N; ++i) {
    allNodes[i]->next = allNodes[i + 1];
  }
  return allNodes[0];
}

int main() {
  auto l1 = list_linear1();
  auto l2 = list_cyclic1();
  auto l3 = list_linear2<6>();
  __builtin_trap();
  return 0;
}