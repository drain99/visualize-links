#include "../tests/common.h"

class Solution {
public:
    ListNode* reverseKGroup(ListNode* head, int k) {
        ListNode* dummy = new ListNode();
        dummy->next = head;
        bool first = true;
        ListNode* ret = head;

        while (true) {
            ListNode* r = getRightBoundary(dummy, k);
            if (not r) return ret;
            
            auto l1 = dummy->next;
            auto nextdummy = dummy->next;
            auto rn = r->next;
            auto rev = rn;
            while (l1 != r) {
                auto tmp = l1->next;
                l1->next = rev;
                rev = l1;
                l1 = tmp;
            }
            l1->next = rev;
            dummy->next = r;
            dummy = nextdummy;
            if (first) { ret = r; first = false; }
        }
        return nullptr;
    }

    ListNode* getRightBoundary(ListNode* oneoffl, int k) {
        for (int i = 0; i < k; ++i) {
            oneoffl = oneoffl->next;
            if (not oneoffl) return nullptr;
        }
        return oneoffl;
    }
};

template <size_t N> ListNode *iota() {
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
  auto l = iota<5>();
  auto sol = Solution();

  auto l2 = sol.reverseKGroup(l, 3);
  __builtin_trap();
  return 0;
}