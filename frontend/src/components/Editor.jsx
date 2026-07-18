import { useEffect, useRef } from "react";
import { Crepe } from "@milkdown/crepe";
import { insert } from "@milkdown/kit/utils";
import { mermaidPlugin } from "../editor/mermaidPlugin.js";
import "@milkdown/crepe/theme/common/style.css";
import "@milkdown/crepe/theme/nord.css";

const INK_SRC_RE = /\/api\/attachments\/([^/?#]+\.svg)/;

/**
 * WYSIWYG markdown editor (Milkdown Crepe).
 *
 * Controlled by `initialValue` on mount only — Crepe owns the document after
 * that. Edits are pushed back as markdown via `onChange` (debounced upstream).
 * `key` the parent on the note path so switching notes remounts the editor.
 *
 * onReady({ insertMarkdown }) — hands the parent a way to insert markdown (used
 *   to drop an ink image at the cursor).
 * onEditInk(name, imgEl) — fired when an existing ink image is clicked, so the
 *   parent can reopen it in the sketch editor.
 */
export default function Editor({ initialValue = "", onChange, onReady, onEditInk }) {
  const rootRef = useRef(null);
  const crepeRef = useRef(null);
  const onChangeRef = useRef(onChange);
  const onReadyRef = useRef(onReady);
  const onEditInkRef = useRef(onEditInk);
  onChangeRef.current = onChange;
  onReadyRef.current = onReady;
  onEditInkRef.current = onEditInk;

  useEffect(() => {
    let destroyed = false;
    const host = rootRef.current;

    const crepe = new Crepe({ root: host, defaultValue: initialValue });
    // Live Mermaid preview under ```mermaid fences (added before create()).
    crepe.editor.use(mermaidPlugin);
    crepe.on((listener) => {
      listener.markdownUpdated((_ctx, markdown) => onChangeRef.current?.(markdown));
    });

    crepe.create().then(() => {
      if (destroyed) {
        crepe.destroy();
        return;
      }
      crepeRef.current = crepe;
      onReadyRef.current?.({
        insertMarkdown: (md) => {
          try {
            crepe.editor.action(insert(md));
          } catch (err) {
            console.error("insertMarkdown failed", err);
          }
        },
      });
    });

    // Reopen ink images for editing. Capture phase so we win over Crepe's own
    // image UI; we only act on Jottr ink attachments (.svg under /attachments).
    const onClick = (e) => {
      const img = e.target?.closest?.("img");
      if (!img) return;
      const m = INK_SRC_RE.exec(img.getAttribute("src") || "");
      if (!m) return;
      onEditInkRef.current?.(m[1], img);
    };
    host.addEventListener("click", onClick, true);

    return () => {
      destroyed = true;
      host?.removeEventListener("click", onClick, true);
      crepeRef.current?.destroy();
      crepeRef.current = null;
    };
    // Mount-only: remount via `key` when the note changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return <div ref={rootRef} className="milkdown-host h-full" />;
}
