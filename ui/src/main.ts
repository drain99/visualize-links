// Copyright (c) Indrajit Banerjee
// Licensed under the MIT License.

import * as d3 from 'd3';
import * as cola from 'webcola';

import * as M from "./model";

const WS_URL = "ws://localhost:8765";

let WS_CLIENT: WebSocket | null = null;

const canvasDiv = document.getElementById("canvasDiv");
const rect = canvasDiv.getBoundingClientRect();
const WIDTH = rect.width;
const HEIGHT = rect.height;

const title = d3.select("#title");
const canvasSvg = d3.select("#canvasSvg").attr("viewBox", `0 0 ${WIDTH} ${HEIGHT}`);
const canvas = canvasSvg.select("#canvas");
const historyCanvas = d3.select("#historyItemListDiv");

canvasSvg.call(
  d3.zoom()
    .on("zoom", () => canvas.attr("transform", d3.event.transform))
);

const compareBtn = document.getElementById("compareBtn")!;
const modal = document.getElementById("compareModal")!;
const oldSelect = document.getElementById("oldSelect")!;
const newSelect = document.getElementById("newSelect")!;
const cancelBtn = document.getElementById("cancelCompareBtn")!;
const confirmBtn = document.getElementById("confirmCompareBtn")!;
let currentHistory: M.History = [];

// node margin helps keep space between node & edge boundaries
const nodeMargin = 4;
// pad is the inner space between node's boundary and its label text
const nodePad = 8;
// extra space used when computing link lengths based on label width
const linkPad = 10;

function renderGraph(graph: M.Graph) {
  showLoadingScreen();

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
    .avoidOverlaps(true);

  console.log("simulation", simulation);

  const valueLinks = graph.links.filter(link => link.tag === "value");
  const valueLinksLine = canvas.selectAll(".valueLink")
    .data(valueLinks)
    .enter().append("line").classed("valueLink", true)
    .attr("marker-end", "url(#arrowheadEndMarker)")
    .attr("marker-start", valueLink => (valueLink.backward_labels.length > 0) ? "url(#arrowheadStartMarker)" : null)

  // TODO: rendering logic for self-loops
  const valueSelfLinks = graph.selfLinks;

  const styles = getComputedStyle(document.documentElement);
  const noneDiffColor = styles.getPropertyValue("--color-btn-primary-bg-hover").trim();
  const oldDiffColor = styles.getPropertyValue("--color-ok-text").trim();
  const newDiffColor = styles.getPropertyValue("--color-bad-text").trim();
  const applyDiffColor = (d: M.Link | M.LinkLabel) => {
    switch (d.diff_type) {
      case '': return noneDiffColor;
      case 'old': return oldDiffColor;
      case 'new': return newDiffColor;
    }
  }

  const nameLinks = graph.links.filter(link => link.tag === "name");
  const nameLinksLine = canvas.selectAll(".nameLink")
    .data(nameLinks)
    .enter().append("line").classed("nameLink", true)
    .style("stroke", applyDiffColor);

  const valueNodes = graph.nodes.filter(node => node.tag === "value");
  const valueNodesRect = canvas.selectAll(".valueNode")
    .data(valueNodes)
    .enter().append("rect").classed("valueNode", true);

  const nameNodes = graph.nodes.filter(node => node.tag === "name");
  const nameNodesRect = canvas.selectAll(".nameNode")
    .data(nameNodes)
    .enter().append("rect").classed("nameNode", true);

  const valueNodesText = canvas.selectAll(".valueNodeLabel")
    .data(valueNodes)
    .enter().append("text").classed("valueNodeLabel", true);

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

  const nameNodesText = canvas.selectAll(".nameNodeLabel")
    .data(nameNodes)
    .enter().append("text").classed("nameNodeLabel", true);

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

  const valueLinkForwardText = canvas.selectAll(".valueLinkForwardLabel")
    .data(valueLinks)
    .enter().append("text").classed("valueLinkForwardLabel", true);

  const valueLinkForwardTspan = valueLinkForwardText.selectAll("tspan")
    .data(valueLink => valueLink.forward_labels)
    .enter().append("tspan")
    .attr("x", 0)
    .attr("dy", (_, i) => (i === 0) ? 0 : "-1.2em")
    .text(linkLabel => linkLabel.label)
    .style("stroke", applyDiffColor)

  valueLinkForwardText
    .each(function (valueLink) {
      // compute link line length based on forward label
      const width = this.getBBox().width;
      const sourceRadius = Math.hypot(valueLink.source.width! / 2, valueLink.source.height! / 2);
      const targetRadius = Math.hypot(valueLink.target.width! / 2, valueLink.target.height! / 2);
      valueLink.length = width + sourceRadius + targetRadius + linkPad;
    });

  const valueLinkBackwardText = canvas.selectAll(".valueLinkBackwardLabel")
    .data(valueLinks)
    .enter().append("text").classed("valueLinkBackwardLabel", true);

  const valueLinkBackwardTspan = valueLinkBackwardText.selectAll("tspan")
    .data(valueLink => valueLink.backward_labels)
    .enter().append("tspan")
    .attr("x", 0)
    .attr("dy", (_, i) => (i === 0) ? 0 : "1.2em")
    .text(linkLabel => linkLabel.label)
    .style("stroke", applyDiffColor)

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

  function tick() {
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

  }

  simulation.on("tick", tick);
  simulation.on("end", hideLoadingScreen);

  simulation.start(25, 50, 50);
  [valueNodesRect, nameNodesRect, valueNodesText, nameNodesText].forEach(d => d.call(simulation.drag));

  // TODO: implement graph freeze support
  // const manualDrag = d3.drag()
  //   .on("start", () => { })
  //   .on("drag", function (node: M.ColaNode) {
  //     node.x = d3.event.x;
  //     node.y = d3.event.y;
  //     const dx = d3.event.dx;
  //     const dy = d3.event.dy;
  //     node.bounds!.x += dx;
  //     node.bounds!.X += dx;
  //     node.bounds!.y += dy;
  //     node.bounds!.Y += dy;
  //   })
  //   .on("end", () => { });

  // document.getElementById("freezeCheckbox")!.addEventListener("change", function () {
  //   if (this.checked) {
  //     simulation.stop();
  //     [valueNodesRect, nameNodesRect, valueNodesText, nameNodesText].forEach(d => d.on(".drag", null));
  //     [valueNodesRect, nameNodesRect, valueNodesText, nameNodesText].forEach(d => d.call(manualDrag));
  //   } else {
  //     simulation.start(25, 50, 50);
  //     [valueNodesRect, nameNodesRect, valueNodesText, nameNodesText].forEach(d => d.on(".drag", null));
  //     [valueNodesRect, nameNodesRect, valueNodesText, nameNodesText].forEach(d => d.call(simulation.drag));
  //   }
  // });
}

function renderHistory(history: M.History) {
  currentHistory = history;
  console.log(history);

  // reset render
  historyCanvas.selectAll("*").remove();

  historyCanvas.selectAll(".historyItem")
    .data(history)
    .enter().append("div").classed("historyItem", true)
    .each(function (item) {
      d3.select(this)
        .append("p")
        .text(`#${item.index}`);

      d3.select(this)
        .append("p")
        .text(`${item.label.function_name}`);

      d3.select(this)
        .append("p")
        .text(`${item.label.filename}:${item.label.line}:${item.label.column}`);

      d3.select(this)
        .append("p")
        .text(`${item.label.desc}`);
    })
    .on("click", item => {
      if (WS_CLIENT) {
        showLoadingScreen();
        WS_CLIENT.send(JSON.stringify({ type: "graph", index: item.index }));
      }
    });
}

function setTitle(t: string) {
  title.text(`Active: ${t}`);
}

function setStatus(text: string, cls: string) {
  d3.select("#status")
    .attr("class", `status ${cls}`)
    .text(text);
}

function showLoadingScreen(message = "Loading graph…") {
  document.getElementById("loadingText")!.textContent = message;
  document.getElementById("loadingScreenDiv")!.classList.add("visible");
}

function hideLoadingScreen() {
  document.getElementById("loadingScreenDiv")!.classList.remove("visible");
}

function populateCompareSelects() {
  [oldSelect, newSelect].forEach(select => {
    select.innerHTML = "";
    currentHistory.forEach(hi => {
      const opt = document.createElement("option");
      opt.value = `${hi.index}`;
      opt.textContent = `#${hi.index}`;
      select.appendChild(opt);
    });
  });
}

compareBtn.addEventListener("click", () => {
  populateCompareSelects();
  modal.classList.remove("hidden");
});

cancelBtn.addEventListener("click", () => {
  modal.classList.add("hidden");
});

confirmBtn.addEventListener("click", () => {
  const oldIndex = Number(oldSelect.value);
  const newIndex = Number(newSelect.value);
  modal.classList.add("hidden");
  if (WS_CLIENT) {
    showLoadingScreen();
    WS_CLIENT.send(JSON.stringify({ type: "diff_graph", old_index: oldIndex, new_index: newIndex }));
  }
});

function connect() {
  setStatus('connecting…', 'warn');
  const ws = new WebSocket(WS_URL);

  ws.onopen = () => {
    setStatus('connected', 'ok');
    WS_CLIENT = ws;
    ws.send(JSON.stringify({ type: 'history' }));
  };

  ws.onmessage = (event: MessageEvent<string>) => {
    try {
      const data: M.Data = JSON.parse(event.data);

      if (data.type === "history") {
        renderHistory(data.history);
      } else if (data.type === "graph") {
        setTitle(data.title);
        if (data.history) {
          renderHistory(data.history);
        }
        renderGraph(data.graph);
      }
    } catch (e) {
      console.error('Invalid graph message:', e);
      setStatus('error rendering graph', 'bad');
    }
  };

  ws.onerror = () => {
    setStatus('connection error', 'bad');
    WS_CLIENT = null;
  };

  ws.onclose = () => {
    setStatus('disconnected — retrying', 'bad');
    WS_CLIENT = null;
    setTimeout(connect, 1000);
  };
}

connect()
