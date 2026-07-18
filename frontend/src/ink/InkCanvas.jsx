import { useRef } from "react";
import { getStroke } from "perfect-freehand";
import { DEFAULT_COLOR, DEFAULT_SIZE, getSvgPathFromStroke } from "./inkSvg.js";

const FREEHAND = { thinning: 0.6, smoothing: 0.5, streamline: 0.5 };

function pathFor(stroke, fallbackSize) {
  const outline = getStroke(stroke.points, {
    size: stroke.size ?? fallbackSize,
    ...FREEHAND,
    simulatePressure: !stroke.hasPressure,
  });
  return getSvgPathFromStroke(outline);
}

/**
 * Freehand drawing surface (perfect-freehand). Controlled: the parent owns the
 * committed `strokes` array (so it can undo/clear); this component only tracks
 * the in-progress stroke, rendering it imperatively for smoothness, and calls
 * `onCommit(stroke)` on pointer-up.
 */
export default function InkCanvas({
  strokes = [],
  onCommit,
  color = DEFAULT_COLOR,
  size = DEFAULT_SIZE,
  width = 640,
  height = 320,
}) {
  const svgRef = useRef(null);
  const liveRef = useRef(null);
  const drawing = useRef(false);
  const points = useRef([]);

  const toLocal = (e) => {
    const rect = svgRef.current.getBoundingClientRect();
    return [
      ((e.clientX - rect.left) / rect.width) * width,
      ((e.clientY - rect.top) / rect.height) * height,
      e.pressure && e.pressure > 0 ? e.pressure : 0.5,
    ];
  };

  const renderLive = () => {
    if (!liveRef.current) return;
    const outline = getStroke(points.current, { size, ...FREEHAND, simulatePressure: false });
    liveRef.current.setAttribute("d", getSvgPathFromStroke(outline));
    liveRef.current.setAttribute("fill", color);
  };

  const onPointerDown = (e) => {
    e.currentTarget.setPointerCapture(e.pointerId);
    drawing.current = true;
    points.current = [toLocal(e)];
    renderLive();
  };

  const onPointerMove = (e) => {
    if (!drawing.current) return;
    points.current.push(toLocal(e));
    renderLive();
  };

  const onPointerUp = () => {
    if (!drawing.current) return;
    drawing.current = false;
    if (points.current.length > 1) {
      onCommit?.({ color, size, hasPressure: true, points: points.current });
    }
    points.current = [];
    liveRef.current?.setAttribute("d", "");
  };

  return (
    <svg
      ref={svgRef}
      viewBox={`0 0 ${width} ${height}`}
      className="h-full w-full touch-none select-none rounded-lg bg-white"
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerLeave={onPointerUp}
    >
      {strokes.map((s, i) => (
        <path key={i} d={pathFor(s, size)} fill={s.color || DEFAULT_COLOR} />
      ))}
      <path ref={liveRef} />
    </svg>
  );
}
