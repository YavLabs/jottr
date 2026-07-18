/**
 * Live Mermaid preview for the Milkdown/Crepe editor.
 *
 * Rather than replacing Crepe's code-block node view, this adds a ProseMirror
 * widget decoration *beneath* every ```mermaid fence that renders the diagram.
 * You keep editing the source in place and see the picture update — WYSIWYG,
 * with markdown still the source of truth.
 *
 * Mermaid is lazy-imported the first time a diagram renders, so it stays out of
 * the initial bundle.
 */

import { $prose } from "@milkdown/kit/utils";
import { Plugin, PluginKey } from "@milkdown/kit/prose/state";
import { Decoration, DecorationSet } from "@milkdown/kit/prose/view";

const key = new PluginKey("jottr-mermaid");
const svgCache = new Map(); // trimmed code -> rendered svg
let seq = 0;
let mermaidPromise = null;

function loadMermaid() {
  if (!mermaidPromise) {
    mermaidPromise = import("mermaid").then(({ default: mermaid }) => {
      const dark = window.matchMedia?.("(prefers-color-scheme: dark)").matches;
      mermaid.initialize({
        startOnLoad: false,
        securityLevel: "strict",
        theme: dark ? "dark" : "default",
        fontFamily: "inherit",
      });
      return mermaid;
    });
  }
  return mermaidPromise;
}

function isMermaidBlock(node) {
  return (
    node.type.name === "code_block" &&
    (node.attrs?.language || "").trim().toLowerCase() === "mermaid"
  );
}

function buildPreview(code) {
  const dom = document.createElement("div");
  dom.className = "jottr-mermaid";
  dom.setAttribute("contenteditable", "false");

  const trimmed = (code || "").trim();
  if (!trimmed) {
    dom.classList.add("jottr-mermaid-empty");
    dom.textContent = "Empty diagram";
    return dom;
  }
  if (svgCache.has(trimmed)) {
    dom.innerHTML = svgCache.get(trimmed);
    return dom;
  }

  dom.textContent = "Rendering diagram…";
  const id = `jottr-mmd-${++seq}`;
  loadMermaid()
    .then((mermaid) => mermaid.render(id, trimmed))
    .then(({ svg }) => {
      svgCache.set(trimmed, svg);
      dom.innerHTML = svg;
    })
    .catch((err) => {
      dom.classList.add("jottr-mermaid-error");
      dom.textContent = `Mermaid error: ${err?.message || err}`;
    });
  return dom;
}

function buildDecorations(doc) {
  const decos = [];
  doc.descendants((node, pos) => {
    if (isMermaidBlock(node)) {
      const code = node.textContent;
      const at = pos + node.nodeSize; // just after the code block
      decos.push(
        Decoration.widget(at, () => buildPreview(code), {
          side: 1,
          key: `mmd:${at}:${code}`,
          ignoreSelection: true,
        }),
      );
      return false;
    }
    return undefined;
  });
  return DecorationSet.create(doc, decos);
}

export const mermaidPlugin = $prose(
  () =>
    new Plugin({
      key,
      state: {
        init: (_config, { doc }) => buildDecorations(doc),
        apply(tr, old) {
          // Only rebuild (and re-render) when the document actually changed.
          return tr.docChanged ? buildDecorations(tr.doc) : old.map(tr.mapping, tr.doc);
        },
      },
      props: {
        decorations(state) {
          return key.getState(state);
        },
      },
    }),
);
