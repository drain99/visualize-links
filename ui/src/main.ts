import * as d3 from 'd3';
import * as cola from 'webcola';

const WS_URL = "ws://localhost:8765";
const WIDTH = 1200
const HEIGHT = 800

// const fixedNodeIds = new Set();

// const nodePositions = new Map();

const canvasSvg = d3.select("#canvas-svg")
  .attr("viewBox", `0 0 ${WIDTH} ${HEIGHT}`);

const canvas = canvasSvg.select("#canvas");

canvasSvg.call(
  d3.zoom()
    .on("zoom", () => canvas.attr("transform", d3.event.transform))
);

// group pad helps keep a minimum distance between name groups and value nodes
const nameGroupPad = 20;
// node margin helps keep space between node & edge boundaries
const nodeMargin = 4;
// pad is the inner space between node's boundary and its label text
const nodePad = 8;

function render(data: string) {
  const color = d3.scaleOrdinal(d3.schemeCategory20);

  const graph = JSON.parse(data);
  console.log("graph:", graph);

  // reset render
  canvas.selectAll("*").remove();

  // start simulation with fixed nodes
  // graph.nodes.forEach(node => {
  //   if (fixedNodeIds.has(node.id)) {
  //     node.fixed = true;
  //   }
  // });

  // graph.nodes.forEach(node => {
  //   if (nodePositions.has(node.id)) {
  //     console.log("using known position");
  //     const pos = nodePositions.get(node.id);
  //     node.x = pos.x;
  //     node.y = pos.y;
  //     node.bounds = pos.bounds;
  //   }
  // })

  // set group padding & make target point to node itself instead of index into node array
  graph.links.forEach(link => {
    link.source = graph.nodes[link.source];
    link.target = graph.nodes[link.target];
  });

  graph.groups.forEach(group => {
    group.padding = nameGroupPad;
    for (const label in group.links) {
      group.links[label].forEach((index, i, links) => {
        links[i] = graph.nodes[index];
      })
    }
  });

  // { group, label, targetNode, [links] }

  const groupLinks = []
  graph.groups.forEach(group => {
    for (const label in group.links) {
      group.links[label].forEach(target => {
        groupLinks.push({
          group: group,
          label: label,
          target: target,
        });
      })
    }
  })

  const simulation = cola.d3adaptor(d3)
    .nodes(graph.nodes)
    .links(graph.links)
    .groups(graph.groups)
    .size([WIDTH, HEIGHT])
    .linkDistance(d => {
      if (d.source.tag === "name" && d.target.tag === "value") {
        return 25;
      }
      return d.length;
    })
    .avoidOverlaps(true)

  const nameGroups = canvas.selectAll(".name-group")
    .data(graph.groups)
    .enter().append("rect").classed("name-group", true)
    .style("fill", color("name-group"))
    .call(simulation.drag)

  const valueLinks = canvas.selectAll(".value-link")
    .data(graph.links.filter(link => link.tag === "value"))
    .enter().append("line").classed("value-link", true);

  const nameLinks = canvas.selectAll(".name-link")
    .data(groupLinks)
    .enter().append("line").classed("name-link", true)
    .each(d => function (d) {
      // need to map back to the simulation links
    })

  const valueNodes = canvas.selectAll(".value-node")
    .data(graph.nodes.filter(node => node.tag === "value"))
    .enter().append("rect").classed("value-node", true)
    .style("fill", color("value-node"))
    .call(simulation.drag);

  const nameNodes = canvas.selectAll(".name-node")
    .data(graph.nodes.filter(node => node.tag === "name"))
    .enter().append("rect").classed("name-node", true)
    .style("fill", color("name-node"))
    .call(simulation.drag)
  // .on('dblclick', function (d) {
  //   console.log(d);
  //   d3.event.stopPropagation();
  //   d.fixed = !d.fixed;
  //   fixedNodeIds.add(d.id);
  //   if (d.fixed) {
  //     d3.select(this).style("fill", color("name-node-fixed"));
  //   } else {
  //     d3.select(this).style("fill", color("name-node"));
  //   }
  // });

  const valueNodeLabels = canvas.selectAll(".value-node-label")
    .data(graph.nodes.filter(node => node.tag === "value"))
    .enter().append("text").classed("value-node-label", true)
    .text(d => d.label)
    .call(simulation.drag)
    .each(function (d) {
      // compute bounds of the label's node
      // based on the label's text space with padding and margin.
      const bb = this.getBBox()
      const extra = 2 * nodeMargin + 2 * nodePad;
      d.width = bb.width + extra;
      d.height = bb.height + extra;
    });

  const nameNodeLabels = canvas.selectAll(".name-node-label")
    .data(graph.nodes.filter(node => node.tag === "name"))
    .enter().append("text").classed("name-node-label", true)
    .text(d => d.label)
    .each(function (d) {
      // compute bounds of the label's node
      // based on the label's text space with padding and margin.
      const bb = this.getBBox();
      const extra = 2 * nodeMargin + 2 * nodePad;
      d.width = bb.width + extra;
      d.height = bb.height + extra;
    })
    .call(simulation.drag)
  // .on('dblclick', function (d) {
  //   console.log(d);
  //   d3.event.stopPropagation();
  //   d.fixed = !d.fixed;
  //   fixedNodeIds.add(d.id);
  //   if (d.fixed) {
  //     d3.select(this).style("fill", color("name-node-fixed"));
  //   } else {
  //     d3.select(this).style("fill", color("name-node"));
  //   }
  // });

  const valueLinkLabels = canvas.selectAll(".value-link-label")
    .data(graph.links.filter(link => link.tag === "value"))
    .enter().append("text").classed("value-link-label", true)
    .text(d => d.label)
    .each(function (d) {
      // compute label's text width
      d.length = this.getBBox().width + Math.max(d.source.height, d.source.width) + Math.max(d.target.height, d.target.width) - 2 * nodeMargin;
    });

  const nameLinkLabels = canvas.selectAll(".name-link-label")
    .data(groupLinks)
    .enter().append("text").classed("name-link-label", true)
    .text(d => d.label);

  simulation.start(25, 50, 50);

  document.getElementById("freeze-checkbox")?.addEventListener("change", ev => {
    if (ev.target.checked) {
      simulation.stop();
      // graph.nodes.forEach(node => node.fixed = true);
    } else {
      // graph.nodes.forEach(node => node.fixed = false);
      simulation.resume();
    }
  });

  simulation.on("tick", () => {
    // console.log("storing node positions...");
    // graph.nodes.forEach(node => {
    //   console.log(node);
    //   nodePositions.set(node.id, { x: node.x, y: node.y, bounds: node.bounds });
    // });

    // compute inner bounds for nodes (with labels) & groups (with nodes)
    valueNodes.each(d => d.innerBounds = d.bounds.inflate(-nodeMargin));
    nameNodes.each(d => d.innerBounds = d.bounds.inflate(-nodeMargin));
    nameGroups.each(d => d.innerBounds = d.bounds.inflate(-nameGroupPad));

    // compute routes for edges
    valueLinks.each(d => d.route = cola.makeEdgeBetween(d.source.innerBounds, d.target.innerBounds, nodePad + 1));
    nameLinks.each(d => d.route = cola.makeEdgeBetween(d.group.innerBounds, d.target.innerBounds, nodePad + 1));

    // render everything in order of definition
    nameGroups
      .attr("x", d => d.innerBounds.x)
      .attr("y", d => d.innerBounds.y)
      .attr("width", d => d.innerBounds.width())
      .attr("height", d => d.innerBounds.height());

    valueLinks
      .attr("x1", d => d.route.sourceIntersection.x)
      .attr("y1", d => d.route.sourceIntersection.y)
      .attr("x2", d => d.route.arrowStart.x)
      .attr("y2", d => d.route.arrowStart.y);

    nameLinks
      // .each(d => console.log("nameLinks:", d, d.route))
      .attr("x1", d => d.route.sourceIntersection.x)
      .attr("y1", d => d.route.sourceIntersection.y)
      .attr("x2", d => d.route.arrowStart.x)
      .attr("y2", d => d.route.arrowStart.y);

    valueNodes
      .attr("x", d => d.innerBounds.x)
      .attr("y", d => d.innerBounds.y)
      .attr("width", d => d.innerBounds.width())
      .attr("height", d => d.innerBounds.height());

    nameNodes
      .attr("x", d => d.innerBounds.x)
      .attr("y", d => d.innerBounds.y)
      .attr("width", d => d.innerBounds.width())
      .attr("height", d => d.innerBounds.height());

    valueNodeLabels
      .attr("x", d => d.innerBounds.cx())
      .attr("y", function (d) {
        const h = this.getBBox().height;
        return d.innerBounds.cy() + h / 4;
      });

    nameNodeLabels
      .attr("x", d => d.innerBounds.cx())
      .attr("y", function (d) {
        const h = this.getBBox().height;
        return d.innerBounds.cy() + h / 4;
      });

    valueLinkLabels
      .attr("x", d => (d.route.sourceIntersection.x + d.route.arrowStart.x) / 2)
      .attr("y", d => (d.route.sourceIntersection.y + d.route.arrowStart.y) / 2)
      .attr("transform", function (d) {
        const source = d.route.sourceIntersection;
        const target = d.route.arrowStart;

        const cx = (source.x + target.x) / 2;
        const cy = (source.y + target.y) / 2;
        const dx = target.x - source.x;
        const dy = target.y - source.y;

        // compute rotation in degrees
        let angle = Math.atan2(dy, dx) * 180 / Math.PI;
        if (angle > 90 || angle < -90) {
          angle += 180;
        }
        return `rotate(${angle} ${cx} ${cy}) translate(0 -2.5)`;
      });

    nameLinkLabels
      // .each(d => console.log("nameLinkLabels:", d, d.route))
      .attr("x", d => (d.route.sourceIntersection.x + d.route.arrowStart.x) / 2)
      .attr("y", d => (d.route.sourceIntersection.y + d.route.arrowStart.y) / 2)
      .attr("transform", function (d) {
        const source = d.route.sourceIntersection;
        const target = d.route.arrowStart;

        const cx = (source.x + target.x) / 2;
        const cy = (source.y + target.y) / 2;
        const dx = target.x - source.x;
        const dy = target.y - source.y;

        // compute rotation in degrees
        let angle = Math.atan2(dy, dx) * 180 / Math.PI;
        if (angle > 90 || angle < -90) {
          angle += 180;
        }
        return `rotate(${angle} ${cx} ${cy}) translate(0 -2.5)`
      });
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
