import * as d3 from 'd3';
import * as cola from 'webcola';

import * as M from "./model";

const WS_URL = "ws://localhost:8765";
const WIDTH = 1200
const HEIGHT = 800

const canvasSvg = d3.select("#canvas-svg")
  .attr("viewBox", `0 0 ${WIDTH} ${HEIGHT}`);

const canvas = canvasSvg.select("#canvas");

canvasSvg.call(
  d3.zoom()
    .on("zoom", () => canvas.attr("transform", d3.event.transform))
);

// node margin helps keep space between node & edge boundaries
const nodeMargin = 4;
// pad is the inner space between node's boundary and its label text
const nodePad = 8;
// extra space used when computing link lengths based on label width
const linkPad = 5;

function render(data: string) {
  const graph: M.ColaModel = JSON.parse(data);
  console.log("graph", graph);

  // reset render
  canvas.selectAll("*").remove();

  // recover internal pointers
  graph.links.forEach(link => {
    link.source = graph.nodes[link.source];
    link.target = graph.nodes[link.target];
  });

  // add extra parent pointers
  graph.links.forEach(link => {
    link.forward_labels.forEach(linkLabel => linkLabel.link = link);
    link.backward_labels.forEach(linkLabel => linkLabel.link = link);
  });

  // extract out self-loops for simulation and rendering
  graph.selfLinks = graph.links.filter(link => link.tag === "value" && link.source == link.target)
  graph.links = graph.links.filter(link => link.source !== link.target)

  const simulation = cola.d3adaptor(d3)
    .nodes(graph.nodes)
    .links(graph.links)
    .size([WIDTH, HEIGHT])
    // link distance is computed on .start() call
    // length attribute wil be filled before that during d3 binding
    .linkDistance(link => link.length!)
    .avoidOverlaps(true)
    .handleDisconnected(true);

  console.log("simulation", simulation);

  const valueLinks = graph.links.filter(link => link.tag === "value");
  const valueLinksLine = canvas.selectAll(".value-link")
    .data(valueLinks)
    .enter().append("line").classed("value-link", true)
    .attr("marker-end", "url(#canvas-arrowhead-end)")
    .attr("marker-start", valueLink => (valueLink.backward_labels.length > 0) ? "url(#canvas-arrowhead-start)" : null)

  // TODO: rendering logic for self-loops
  const valueSelfLinks = graph.selfLinks;

  const nameLinks = graph.links.filter(link => link.tag === "name");
  const nameLinksLine = canvas.selectAll(".name-link")
    .data(nameLinks)
    .enter().append("line").classed("name-link", true)
    .style("stroke", nameLink => {
      switch (nameLink.diff_type) {
        case "": return "#2c2c2c";
        case "old": return "#9f1919ff";
        case "new": return "#18750aff";
      }
    });

  const valueNodes = graph.nodes.filter(node => node.tag === "value");
  const valueNodesRect = canvas.selectAll(".value-node")
    .data(valueNodes)
    .enter().append("rect").classed("value-node", true)
    .call(simulation.drag);

  const nameNodes = graph.nodes.filter(node => node.tag === "name");
  const nameNodesRect = canvas.selectAll(".name-node")
    .data(nameNodes)
    .enter().append("rect").classed("name-node", true)
    .call(simulation.drag);

  const valueNodesText = canvas.selectAll(".value-node-label")
    .data(valueNodes)
    .enter().append("text").classed("value-node-label", true)
    .call(simulation.drag);

  const valueNodesTspan = valueNodesText.selectAll("tspan")
    .data(valueNode => valueNode.label)
    .enter().append("tspan")
    // set to 0 because default starts after previous tspan which inflates
    // the text element's width leading to incorrect width & height computation
    .attr("x", 0)
    .attr("dy", (_, i) => (i === 0) ? 0 : "1.2em")
    .text(labelLine => labelLine);

  valueNodesText
    .attr("transform", function (valueNode) {
      // move to center the text element while preserving left-alignment with text-anchor
      // also adjust vertical alignment
      const bb = this.getBBox();
      return `translate(${-bb.width / 2} ${(3 - 2 * valueNode.label.length) * bb.height / (4 * valueNode.label.length)})`
    })
    .each(function (valueNode) {
      // compute node rect bounds used by cola
      const bb = this.getBBox();
      const extra = 2 * nodeMargin + 2 * nodePad;
      valueNode.width = bb.width + extra;
      valueNode.height = bb.height + extra;
    });

  const nameNodesText = canvas.selectAll(".name-node-label")
    .data(nameNodes)
    .enter().append("text").classed("name-node-label", true)
    .call(simulation.drag);

  const nameNodesTspan = nameNodesText.selectAll("tspan")
    .data(nameNode => nameNode.label)
    .enter().append("tspan")
    // set to 0 because default starts after previous tspan which inflates
    // the text element's width leading to incorrect width & height computation
    .attr("x", 0)
    .attr("dy", (_, i) => (i === 0) ? 0 : "1.2em")
    .text(labelLine => labelLine);

  nameNodesText
    .attr("transform", function (nameNode) {
      // move to center the text element while preserving left-alignment with text-anchor
      // also adjust vertical alignment
      const bb = this.getBBox();
      return `translate(${-bb.width / 2} ${(3 - 2 * nameNode.label.length) * bb.height / (4 * nameNode.label.length)})`
    })
    .each(function (nameNode) {
      // compute node rect bounds used by cola
      const bb = this.getBBox();
      const extra = 2 * nodeMargin + 2 * nodePad;
      nameNode.width = bb.width + extra;
      nameNode.height = bb.height + extra;
    });

  const valueLinkForwardText = canvas.selectAll(".value-link-forward-label")
    .data(valueLinks)
    .enter().append("text").classed("value-link-forward-label", true);

  const valueLinkForwardTspan = valueLinkForwardText.selectAll("tspan")
    .data(valueLink => valueLink.forward_labels)
    .enter().append("tspan")
    .attr("x", 0)
    .attr("dy", (_, i) => (i === 0) ? 0 : "-1.2em")
    .text(linkLabel => linkLabel.label)
    .style("stroke", linkLabel => {
      switch (linkLabel.diff_type) {
        case "": return "#2c2c2c";
        case "old": return "#9f1919ff";
        case "new": return "#18750aff";
      }
    });

  valueLinkForwardText
    .each(function (valueLink) {
      // compute link line length based on forward label
      const width = this.getBBox().width;
      const sourceRadius = Math.hypot(valueLink.source.width! / 2, valueLink.source.height! / 2);
      const targetRadius = Math.hypot(valueLink.target.width! / 2, valueLink.target.height! / 2);
      valueLink.length = width + sourceRadius + targetRadius + linkPad;
    });

  const valueLinkBackwardText = canvas.selectAll(".value-link-backward-label")
    .data(valueLinks)
    .enter().append("text").classed("value-link-backward-label", true);

  const valueLinkBackwardTspan = valueLinkBackwardText.selectAll("tspan")
    .data(valueLink => valueLink.backward_labels)
    .enter().append("tspan")
    .attr("x", 0)
    .attr("dy", (_, i) => (i === 0) ? 0 : "1.2em")
    .text(linkLabel => linkLabel.label)
    .style("stroke", linkLabel => {
      switch (linkLabel.diff_type) {
        case "": return "#2c2c2c";
        case "old": return "#9f1919ff";
        case "new": return "#18750aff";
      }
    });

  valueLinkBackwardText
    .each(function (valueLink) {
      // update link line length based on backward label
      const width = this.getBBox().width;
      const sourceRadius = Math.hypot(valueLink.source.width! / 2, valueLink.source.height! / 2);
      const targetRadius = Math.hypot(valueLink.target.width! / 2, valueLink.target.height! / 2);
      valueLink.length = Math.max(valueLink.length!, width + sourceRadius + targetRadius + linkPad);
    });

  nameLinks.forEach(nameLink => {
    const sourceRadius = Math.hypot(nameLink.source.width! / 2, nameLink.source.height! / 2);
    const targetRadius = Math.hypot(nameLink.target.width! / 2, nameLink.target.height! / 2);
    nameLink.length = sourceRadius + targetRadius + linkPad;
  });

  simulation.start(25, 50, 50);

  // TODO: implement graph freeze support
  // document.getElementById("freeze-checkbox")?.addEventListener("change", ev => {
  //   if (ev.target.checked) {
  //     simulation.stop();
  //     // graph.nodes.forEach(node => node.fixed = true);
  //   } else {
  //     // graph.nodes.forEach(node => node.fixed = false);
  //     simulation.resume();
  //   }
  // });

  simulation.on("tick", () => {
    // compute inner bounds which is used for rendering
    valueNodes.forEach(valueNode => valueNode.renderBounds = valueNode.bounds!.inflate(-nodeMargin));
    nameNodes.forEach(nameNode => nameNode.renderBounds = nameNode.bounds!.inflate(-nodeMargin));

    // compute link routes for rendering
    valueLinks.forEach(valueLink => valueLink.forwardRoute = cola.makeEdgeBetween(valueLink.source.renderBounds!, valueLink.target.renderBounds!, 5));
    valueLinks.forEach(valueLink => valueLink.backwardRoute = cola.makeEdgeBetween(valueLink.target.renderBounds!, valueLink.source.renderBounds!, 5));
    nameLinks.forEach(nameLink => nameLink.forwardRoute = cola.makeEdgeBetween(nameLink.source.renderBounds!, nameLink.target.renderBounds!, 5));

    valueLinksLine
      .attr("x1", valueLink => (valueLink.backward_labels.length > 0) ? valueLink.backwardRoute!.arrowStart.x : valueLink.forwardRoute!.sourceIntersection.x)
      .attr("y1", valueLink => (valueLink.backward_labels.length > 0) ? valueLink.backwardRoute!.arrowStart.y : valueLink.forwardRoute!.sourceIntersection.y)
      .attr("x2", valueLink => valueLink.forwardRoute!.arrowStart.x)
      .attr("y2", valueLink => valueLink.forwardRoute!.arrowStart.y);

    nameLinksLine
      .attr("x1", nameLink => nameLink.forwardRoute!.sourceIntersection.x)
      .attr("y1", nameLink => nameLink.forwardRoute!.sourceIntersection.y)
      .attr("x2", nameLink => nameLink.forwardRoute!.arrowStart.x)
      .attr("y2", nameLink => nameLink.forwardRoute!.arrowStart.y);

    valueNodesRect
      .attr("x", valueNode => valueNode.renderBounds!.x)
      .attr("y", valueNode => valueNode.renderBounds!.y)
      .attr("width", valueNode => valueNode.renderBounds!.width())
      .attr("height", valueNode => valueNode.renderBounds!.height());

    nameNodesRect
      .attr("x", nameNode => nameNode.renderBounds!.x)
      .attr("y", nameNode => nameNode.renderBounds!.y)
      .attr("width", nameNode => nameNode.renderBounds!.width())
      .attr("height", nameNode => nameNode.renderBounds!.height());

    valueNodesText
      .attr("x", valueNode => valueNode.renderBounds!.cx())
      .attr("y", valueNode => valueNode.renderBounds!.cy());

    valueNodesTspan
      .attr("x", function () { return this.parentElement!.getAttribute("x"); });

    nameNodesText
      .attr("x", nameNode => nameNode.renderBounds!.cx())
      .attr("y", nameNode => nameNode.renderBounds!.cy());

    nameNodesTspan
      .attr("x", function () { return this.parentElement!.getAttribute("x"); });

    valueLinkForwardText
      .attr("x", valueLink => (valueLink.forwardRoute!.sourceIntersection.x + valueLink.forwardRoute!.arrowStart.x) / 2)
      .attr("y", valueLink => (valueLink.forwardRoute!.sourceIntersection.y + valueLink.forwardRoute!.arrowStart.y) / 2)
      .attr("transform", valueLink => {
        const source = valueLink.forwardRoute!.sourceIntersection;
        const target = valueLink.forwardRoute!.arrowStart;

        const cx = (source.x + target.x) / 2;
        const cy = (source.y + target.y) / 2;
        const dx = target.x - source.x;
        const dy = target.y - source.y;

        // compute rotation in degrees
        let angle = Math.atan2(dy, dx) * 180 / Math.PI;
        if (angle > 90 || angle < -90) {
          angle += 180;
          valueLink.reverseLabelArrow = true;
        } else {
          valueLink.reverseLabelArrow = false;
        }

        // translate so text is above the line
        return `rotate(${angle} ${cx} ${cy}) translate(0 -3.5)`;
      });

    valueLinkForwardTspan
      .attr("x", function () { return this.parentElement!.getAttribute("x"); })
      .text(linkLabel => linkLabel.link.reverseLabelArrow! ? `←${linkLabel.label}` : `${linkLabel.label}→`);

    valueLinkBackwardText
      .attr("x", valueLink => (valueLink.forwardRoute!.sourceIntersection.x + valueLink.forwardRoute!.arrowStart.x) / 2)
      .attr("y", valueLink => (valueLink.forwardRoute!.sourceIntersection.y + valueLink.forwardRoute!.arrowStart.y) / 2)
      .attr("transform", function (valueLink) {
        const source = valueLink.forwardRoute!.sourceIntersection;
        const target = valueLink.forwardRoute!.arrowStart;

        const cx = (source.x + target.x) / 2;
        const cy = (source.y + target.y) / 2;
        const dx = target.x - source.x;
        const dy = target.y - source.y;

        // compute rotation in degrees
        let angle = Math.atan2(dy, dx) * 180 / Math.PI;
        if (angle > 90 || angle < -90) {
          angle += 180;
          valueLink.reverseLabelArrow = true;
        } else {
          valueLink.reverseLabelArrow = false;
        }

        // translate so text is below the line
        return `rotate(${angle} ${cx} ${cy}) translate(0 ${2.5 + (3 * this.getBBox().height) / 4})`;
      });

    valueLinkBackwardTspan
      .attr("x", function () { return this.parentElement!.getAttribute("x"); })
      .text(linkLabel => linkLabel.link.reverseLabelArrow! ? `${linkLabel.label}→` : `←${linkLabel.label}`);
  });
}

function setStatus(text: string, cls: string) {
  const el = document.getElementById('status');
  el!.textContent = text;
  el!.className = `status ${cls}`;
}

function connect() {
  const ws = new WebSocket(WS_URL);
  setStatus('connecting…', 'warn');

  ws.onopen = () => setStatus('connected', 'ok');

  ws.onmessage = (event: MessageEvent<string>) => {
    try {
      render(event.data);
    } catch (e) {
      console.error('Invalid graph message:', e);
      setStatus('error rendering graph', 'bad');
    }
  };

  ws.onerror = () => setStatus('socket error', 'bad');

  ws.onclose = () => {
    setStatus('disconnected — retrying', 'bad');
    setTimeout(connect, 1000);
  };
}

connect()