"use client";
import { useCallback } from "react";
import useSWR from "swr";
import { api } from "@/lib/api";

function formatTime(s: number): string {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, "0")}`;
}

export default function PlayerBar({
  onToggleQueue,
}: {
  onToggleQueue: () => void;
}) {
  const { data } = useSWR("player-status", api.status, { refreshInterval: 1000 });

  const name = data?.name || "";
  const artist = data?.artist || "";
  const position = data?.position ?? 0;
  const duration = data?.duration ?? 0;
  const playerState = data?.state ?? "stopped";
  const isPlaying = playerState === "playing";
  const progress = duration > 0 ? (position / duration) * 100 : 0;

  const handleSeek = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (!duration) return;
      const rect = e.currentTarget.getBoundingClientRect();
      const ratio = (e.clientX - rect.left) / rect.width;
      api.seek(ratio * duration);
    },
    [duration]
  );

  return (
    <div className="fixed bottom-0 left-0 right-0 h-20 bg-black/90 backdrop-blur-xl backdrop-saturate-[1.8] border-t border-[var(--ds-gray-400)] px-6 flex items-center gap-5 z-50">
      {/* Track Info */}
      <div className="flex items-center gap-3 w-[260px] min-w-0 shrink-0">
        {name ? (
          <img
            key={data?.database_id}
            src={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/player/artwork?t=${data?.database_id}`}
            alt=""
            className="w-12 h-12 rounded border border-[var(--ds-gray-400)] bg-[var(--ds-gray-200)] shrink-0 object-cover"
            onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
          />
        ) : (
          <div className="w-12 h-12 rounded border border-[var(--ds-gray-400)] bg-[var(--ds-gray-200)] flex items-center justify-center text-lg text-[var(--ds-gray-700)] shrink-0">
            ♪
          </div>
        )}
        <div className="min-w-0">
          <div className="text-sm font-medium truncate">{name || "Not Playing"}</div>
          <div className="text-[13px] text-[var(--ds-gray-700)] truncate">{artist}</div>
        </div>
      </div>

      {/* Controls */}
      <div className="flex-1 flex flex-col items-center gap-1.5">
        <div className="flex items-center gap-6">
          <button onClick={() => api.control("prev")} className="w-8 h-8 flex items-center justify-center text-[var(--ds-gray-900)] hover:text-[var(--geist-foreground)] transition-colors duration-150">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M11.5 3H13v10h-1.5V3zM3.5 8L10 3v10L3.5 8z"/></svg>
          </button>
          <button
            onClick={() => api.control(isPlaying ? "pause" : "resume")}
            className="w-9 h-9 rounded-full bg-[var(--geist-foreground)] text-[var(--geist-background)] flex items-center justify-center hover:bg-[#ccc] transition-colors duration-150"
          >
            {isPlaying ? (
              <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><rect x="3" y="2" width="4" height="12" rx="1"/><rect x="9" y="2" width="4" height="12" rx="1"/></svg>
            ) : (
              <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M4 2.5v11l9-5.5L4 2.5z"/></svg>
            )}
          </button>
          <button onClick={() => api.control("next")} className="w-8 h-8 flex items-center justify-center text-[var(--ds-gray-900)] hover:text-[var(--geist-foreground)] transition-colors duration-150">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M3 3h1.5v10H3V3zm9.5 5L6 13V3l6.5 5z"/></svg>
          </button>
        </div>
        <div className="flex items-center gap-2 w-full max-w-[560px]">
          <span className="text-xs text-[var(--ds-gray-700)] font-[family-name:var(--font-geist-mono)] tabular-nums min-w-9 text-center">
            {formatTime(position)}
          </span>
          <div
            className="flex-1 h-1 bg-[var(--ds-gray-alpha-400)] rounded-sm cursor-pointer group relative"
            onClick={handleSeek}
          >
            <div className="h-full bg-[var(--geist-foreground)] rounded-sm relative" style={{ width: `${progress}%` }}>
              <span className="absolute -right-[5px] -top-[3px] w-2.5 h-2.5 rounded-full bg-[var(--geist-foreground)] opacity-0 group-hover:opacity-100 transition-opacity duration-150" />
            </div>
          </div>
          <span className="text-xs text-[var(--ds-gray-700)] font-[family-name:var(--font-geist-mono)] tabular-nums min-w-9 text-center">
            {formatTime(duration)}
          </span>
        </div>
      </div>

      {/* Volume + Queue */}
      <div className="flex items-center gap-3 w-[200px] justify-end shrink-0">
        <VolumeControl volume={data?.volume ?? 50} />
        <button
          onClick={onToggleQueue}
          className="px-3 py-1.5 border border-[var(--ds-gray-400)] rounded-md text-[13px] text-[var(--ds-gray-900)] hover:text-[var(--geist-foreground)] hover:border-[var(--geist-foreground)] transition-all duration-150"
        >
          Queue
        </button>
      </div>
    </div>
  );
}

function VolumeControl({ volume }: { volume: number }) {
  const handleVolumeChange = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const ratio = (e.clientX - rect.left) / rect.width;
    api.setVolume(Math.round(ratio * 100));
  }, []);

  return (
    <div className="flex items-center gap-2">
      <span className="text-sm text-[var(--ds-gray-900)]">♪</span>
      <div className="w-20 h-1 bg-[var(--ds-gray-alpha-400)] rounded-sm cursor-pointer" onClick={handleVolumeChange}>
        <div className="h-full bg-[var(--geist-foreground)] rounded-sm" style={{ width: `${volume}%` }} />
      </div>
    </div>
  );
}
