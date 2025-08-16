#include "common.h"

struct ListNode {
  int val;
  ListNode *next = nullptr;

  ListNode(int val) : val(val) {}
};

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

int main() {
  auto l1 = list_linear1();
  auto l2 = list_cyclic1();
  __builtin_trap();
  return 0;
}