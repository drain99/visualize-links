import * as cola from 'webcola';

export type Tag = "name" | "value";
export type DiffType = "" | "old" | "new";

export type Node = cola.Node & {
  id: string,
  label: string[],
  tag: Tag,
  bounds?: cola.Rectangle,
  renderBounds?: cola.Rectangle,
};

export type LinkLabel = {
  label: string,
  diff_type: DiffType,
  link: Link,
};

export type Route = {
  sourceIntersection: cola.Point;
  targetIntersection: cola.Point;
  arrowStart: cola.Point;
};

export type Link = cola.Link<cola.Node> & {
  source: Node,
  target: Node,
  forward_labels: LinkLabel[],
  backward_labels: LinkLabel[],
  tag: Tag,
  diff_type: DiffType,
  forwardRoute?: Route,
  backwardRoute?: Route,
  reverseLabelArrow?: boolean,
};

export type Graph = {
  nodes: Node[],
  links: Link[],
  selfLinks?: Link[],
};

export type HistoryLabel = {
  filename: string
  line: number
  column: number
  function_name: string
};

export type HistoryItem = {
  index: number,
  label: HistoryLabel,
};

export type History = HistoryItem[];

export type Data = {
  type: "history",
  history: History,
} | {
  type: "graph",
  title: string,
  graph: Graph,
  history?: History,
};
