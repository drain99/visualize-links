from collections import OrderedDict, defaultdict

import model as M
import cola_model as C


def convert_to_cola(g: M.Graph) -> C.Graph:
    nodes: OrderedDict[M.NodeId, C.Node] = OrderedDict()
    node_id2index: dict[M.NodeId, C.NodeIndex] = dict()

    # add value nodes
    for node, desc in g.nodes.items():
        assert node not in nodes, "Node ids must be unique!"

        label = desc.attrs_to_label()

        nodes[node] = C.Node(id=node, label=label, tag="value")
        node_id2index[node] = len(nodes) - 1

    # condense bi-directional links & add value links
    links_condensed: OrderedDict[M.LinkId, C.Link] = OrderedDict()
    for link, desc in g.links.items():
        source, target = link
        source_index = node_id2index[source]
        target_index = node_id2index[target]

        assert (
            link not in links_condensed
        ), "Multi-edges are impossible by construction!"

        if (target, source) in links_condensed:
            # bi-directional edge
            links_condensed[(target, source)].backward_labels = [
                C.LinkLabel(label=l[0], diff_type=l[1])
                for l in desc.accessors_to_label()
            ]
        else:
            # add new edge
            links_condensed[(source, target)] = C.Link(
                source=source_index,
                target=target_index,
                forward_labels=[
                    C.LinkLabel(label=l[0], diff_type=l[1])
                    for l in desc.accessors_to_label()
                ],
                backward_labels=[],
                tag="value",
                diff_type="",
            )

    # condense name nodes & links
    name_adj_list: defaultdict[
        str, defaultdict[M.NameDiffType | None, set[M.NodeId]]
    ] = defaultdict(lambda: defaultdict(set))
    for node, desc in g.nodes.items():
        for name, name_desc in desc.names.items():
            name_adj_list[name][name_desc.diff_type].add(node)

    inv_name_adj_list: defaultdict[
        frozenset[tuple[M.NameDiffType | None, frozenset[M.NodeId]]], list[str]
    ] = defaultdict(list)
    for name, name_links in name_adj_list.items():
        frozen_name_links: frozenset[
            tuple[M.NameDiffType | None, frozenset[M.NodeId]]
        ] = frozenset(
            (name_diff, frozenset(targets)) for name_diff, targets in name_links.items()
        )

        inv_name_adj_list[frozen_name_links].append(name)

    # add name nodes & links
    for name_link, names in inv_name_adj_list.items():
        id = f"NAME{set(names)}"

        nodes[id] = C.Node(id=id, label=names, tag="name")
        node_id2index[id] = len(nodes) - 1

        for name_diff, targets in name_link:
            diff_type: M.DiffType = (
                name_diff if (name_diff == "old" or name_diff == "new") else ""
            )
            source_index = node_id2index[id]
            for target in targets:
                target_index = node_id2index[target]

                assert (
                    id,
                    target,
                ) not in links_condensed, "Algorithm invariant failed!"

                links_condensed[(id, target)] = C.Link(
                    source=source_index,
                    target=target_index,
                    forward_labels=[],
                    backward_labels=[],
                    tag="name",
                    diff_type=diff_type,
                )

    return C.Graph(nodes=list(nodes.values()), links=list(links_condensed.values()))
