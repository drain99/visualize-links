// Copyright (c) Indrajit Banerjee
// Licensed under the MIT License.

#include <list>
#include <tuple>
#include <vector>

#include "common.h"

struct BinaryTreeNode {
  int val;
  BinaryTreeNode *left = nullptr;
  BinaryTreeNode *right = nullptr;

  BinaryTreeNode(int val) : val(val) {}
};

struct VecTreeNode {
  int val;
  std::vector<VecTreeNode *> children;

  VecTreeNode(int val) : val(val) {}
};

struct ListTreeNode {
  int val;
  std::list<VecTreeNode *> children;

  ListTreeNode(int val) : val(val) {}
};

struct TupleTreeNode {
  int val;
  std::tuple<TupleTreeNode *, TupleTreeNode *> children;

  TupleTreeNode(int val) : val(val) {}
};

BinaryTreeNode* binary_tree_linear1() {
  auto [w, x, y, z] = nodes<BinaryTreeNode, 4>();
  w->left = x;
  w->right = y;
  y->left = z;
  return w;
}

BinaryTreeNode* binary_tree_cyclic1() {
auto [w, x, y, z] = nodes<BinaryTreeNode, 4>();
  w->left = x;
  w->right = y;
  y->left = z;
  y->right = w;
  return w;
}

int main() {
  auto t1 = binary_tree_linear1();
  auto t2 = binary_tree_cyclic1();
  __builtin_trap();
  return 0;
}