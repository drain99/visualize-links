# visualize-links
An LLDB debugger plugin and web ui to visualize and debug pointer-based
data structure programs written in C/C++."

`visualize-links` provides a python LLDB plugin with custom commands to visualize program variables
and expressions. It also contains an interactive web ui acting as the canvas where generated graphs are shown.

Pointer-based data structures are represented as graphs where each node represents
a value and each edge represents directed links between values
through member attributes.

<img src="https://raw.githubusercontent.com/drain99/visualize-links/refs/tags/v1.0.1/demo.gif" alt="demo GIF" width="820">

## Installation

Install LLDB. Note that test scripts are hardcoded to use `lldb-19` whenever required.

Install `visualize-links` package and auto-import it on LLDB session start.

```bash
$ pip install visualize-links && echo "command script import visualize_links" >> ~/.lldbinit
```

## Usage
Usage is shown using a sample program that implements the following linked list
problem: [Reverse Nodes in k-Group](https://leetcode.com/problems/reverse-nodes-in-k-group/).

- Given the head of a linked list, reverse the nodes of the list k at a time, and return the modified list.
- The example can be found at [tests/list_reverse_k_group.cpp](tests/list_reverse_k_group.cpp) and ran as follows.

```bash
$ make launch_test TARGET=list_reverse_k_group
```

This performs the following tasks:
  - Builds the target program: `$(TARGET).cpp`
  - Launches ui in browser: `$ visualize-links-ui`
  - Starts an lldb session: `lldb $(TARGET)`
  - Executes a sample set of lldb commands: `$(TARGET).lldb`

The plugin exposes the following lldb commands for visualization.
- `visualize-expr EXPR`
  - Create a graph starting from `EXPR`. Values unreachable from `EXPR` are not traced.
- `visualize-type TYPE`
  - Create a graph starting from all active variables pointing to a value of type `TYPE`.
- `visualize-history`
  - Show a list of past graphs generated with the above two commands along with their unique ids.
  History is also shown on the right pane of the ui.
- `visualize-diff UID1 UID2`
  - Create an asymmetric difference graph showing how the graphs corresponding to `UID1` and `UID2` differ.
  Difference graph can be created from the ui directly as well.

For demonstration, [list_reverse_k_group.lldb](tests/list_reverse_k_group.lldb) is shown below with comments:

```bash
(lldb) # add a breakpoint after the initial list l is created [0,1,2,3,4]
(lldb) b list_reverse_k_group.cpp:63
(lldb) # add a breakpoint after l2 points to the intended new list [2,1,0,3,4]
(lldb) b list_reverse_k_group.cpp:66
(lldb) run
(lldb) # visualize the list pointed by l
(lldb) visualize-expr l
(lldb) continue
(lldb) # visualize the new list pointed by l2
(lldb) visualize-expr l2
(lldb) # visualize lists from l & l2
(lldb) visualize-type ListNode
(lldb) # visualize the transformation performed by reverseKGroup()
(lldb) visualize-diff 0 1
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
