import { useEffect, useRef } from "react";
import { Crepe } from "@milkdown/crepe";
import "@milkdown/crepe/theme/common/style.css";
import "@milkdown/crepe/theme/nord.css";

/**
 * WYSIWYG markdown editor (Milkdown Crepe).
 *
 * Controlled by `initialValue` on mount only — Crepe owns the document after
 * that. Edits are pushed back as markdown via `onChange` (debounced upstream).
 * `key` the parent on the note path so switching notes remounts the editor.
 */
export default function Editor({ initialValue = "", onChange }) {
  const rootRef = useRef(null);
  const crepeRef = useRef(null);
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;

  useEffect(() => {
    let destroyed = false;
    const crepe = new Crepe({
      root: rootRef.current,
      defaultValue: initialValue,
    });

    crepe.on((listener) => {
      listener.markdownUpdated((_ctx, markdown) => {
        onChangeRef.current?.(markdown);
      });
    });

    crepe.create().then(() => {
      if (destroyed) crepe.destroy();
      else crepeRef.current = crepe;
    });

    return () => {
      destroyed = true;
      crepeRef.current?.destroy();
      crepeRef.current = null;
    };
    // Mount-only: remount via `key` when the note changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return <div ref={rootRef} className="milkdown-host h-full" />;
}
