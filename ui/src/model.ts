import * as cola from 'webcola';

export type ColaTag = "name" | "value";
export type ColaDiffType = "" | "old" | "new";

export type ColaNode = cola.Node & {
  id: string,
  label: string[],
  tag: ColaTag,
  bounds?: cola.Rectangle,
  renderBounds?: cola.Rectangle,
};

export type ColaLinkLabel = {
  label: string,
  diff_type: ColaDiffType,
  link: ColaLink,
};

export type ColaRoute = {
  sourceIntersection: cola.Point;
  targetIntersection: cola.Point;
  arrowStart: cola.Point;
};

export type ColaLink = cola.Link<cola.Node> & {
  source: ColaNode,
  target: ColaNode,
  forward_labels: ColaLinkLabel[],
  backward_labels: ColaLinkLabel[],
  tag: ColaTag,
  diff_type: ColaDiffType,
  forwardRoute?: ColaRoute,
  backwardRoute?: ColaRoute,
  reverseLabelArrow?: boolean,
};

export type ColaModel = {
  nodes: ColaNode[],
  links: ColaLink[],
  selfLinks: ColaLink[],
};
