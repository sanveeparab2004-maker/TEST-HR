import React, { useEffect, useRef, useState } from "react";
import { Camera, ShieldAlert } from "lucide-react";

interface SelfCameraTileProps {
  stream: MediaStream | null;
  warningCount: number;
}

export const SelfCameraTile: React.FC<SelfCameraTileProps> = ({ stream, warningCount }) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [position, setPosition] = useState({ x: 24, y: 24 });
  const [isDragging, setIsDragging] = useState(false);
  const dragRef = useRef({ startX: 0, startY: 0, initX: 24, initY: 24 });

  useEffect(() => {
    if (videoRef.current && stream) {
      videoRef.current.srcObject = stream;
    }
  }, [stream]);

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    dragRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      initX: position.x,
      initY: position.y,
    };
  };

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging) return;
      const dx = e.clientX - dragRef.current.startX;
      const dy = e.clientY - dragRef.current.startY;
      setPosition({
        x: Math.max(10, Math.min(window.innerWidth - 180, dragRef.current.initX + dx)),
        y: Math.max(10, Math.min(window.innerHeight - 150, dragRef.current.initY + dy)),
      });
    };

    const handleMouseUp = () => setIsDragging(false);

    if (isDragging) {
      window.addEventListener("mousemove", handleMouseMove);
      window.addEventListener("mouseup", handleMouseUp);
    }
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isDragging]);

  return (
    <div
      style={{ right: `${position.x}px`, bottom: `${position.y}px` }}
      className="fixed z-30 select-none transition-shadow duration-200"
    >
      <div className="w-40 sm:w-48 bg-slate-900 rounded-xl overflow-hidden border border-slate-700 shadow-xl shadow-slate-950/20">
        {/* Drag Bar & Status */}
        <div
          onMouseDown={handleMouseDown}
          className="bg-slate-800/90 backdrop-blur-sm px-2.5 py-1.5 flex items-center justify-between cursor-move text-[11px] text-slate-300 font-medium"
        >
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span>Live Proctor</span>
          </div>

          <div className="flex items-center gap-1">
            {warningCount > 0 && (
              <span
                className={`px-1.5 py-0.2 rounded text-[10px] font-bold ${
                  warningCount >= 4
                    ? "bg-rose-500 text-white animate-pulse"
                    : "bg-amber-500 text-slate-950"
                }`}
              >
                {warningCount >= 4 ? "FINAL" : `${warningCount}/3`}
              </span>
            )}
          </div>
        </div>

        {/* Video stream */}
        <div className="relative aspect-[4/3] bg-black">
          {stream ? (
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className="w-full h-full object-cover -scale-x-100"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-slate-500">
              <Camera className="w-6 h-6 animate-pulse" />
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
