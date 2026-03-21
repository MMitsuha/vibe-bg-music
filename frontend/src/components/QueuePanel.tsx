"use client";
import useSWR from "swr";
import { api } from "@/lib/api";

export default function QueuePanel({
  visible,
  onClose,
}: {
  visible: boolean;
  onClose: () => void;
}) {
  const { data, mutate } = useSWR(visible ? "queue" : null, api.queue, { refreshInterval: 2000 });

  const queue = data?.queue ?? [];
  const currentIndex = data?.current_index ?? 0;

  async function handleRemove(index: number) {
    await api.removeFromQueue(index);
    mutate();
  }

  async function handleJump(index: number) {
    await api.jumpTo(index);
    mutate();
  }

  if (!visible) return null;

  return (
    <div className="fixed right-4 bottom-[88px] w-[360px] max-h-[400px] bg-[var(--ds-background-200)] border border-[var(--ds-gray-400)] rounded-lg p-4 overflow-y-auto z-40">
      <div className="flex items-center justify-between mb-3">
        <span className="text-[13px] font-semibold text-[var(--ds-gray-900)] uppercase tracking-wider">
          Up Next
        </span>
        <button
          onClick={onClose}
          className="p-1 text-[var(--ds-gray-900)] hover:text-[var(--geist-foreground)] transition-colors duration-150 rounded"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M4 6L8 10L12 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
      </div>

      {queue.map((track, i) => (
        <div
          key={`${track.database_id}-${i}`}
          className="flex items-center justify-between px-2 py-2 rounded-md transition-colors duration-150 hover:bg-[var(--ds-gray-alpha-200)] cursor-pointer"
          onClick={() => i !== currentIndex && handleJump(i)}
        >
          <div className="min-w-0 flex flex-col gap-0.5">
            <span className={`text-[13px] truncate ${i === currentIndex ? "text-[var(--geist-foreground)] font-medium" : "text-[var(--ds-gray-900)]"}`}>
              {track.name}
            </span>
            <span className="text-xs text-[var(--ds-gray-700)]">{track.artist}</span>
          </div>
          {i === currentIndex ? (
            <span className="text-[11px] font-medium text-[var(--geist-foreground)] shrink-0">Playing</span>
          ) : (
            <button
              onClick={(e) => { e.stopPropagation(); handleRemove(i); }}
              className="w-6 h-6 flex items-center justify-center text-[var(--accents-3)] hover:text-[var(--geist-foreground)] hover:bg-[var(--ds-gray-alpha-200)] rounded transition-colors duration-150 shrink-0"
            >
              ×
            </button>
          )}
        </div>
      ))}

      {queue.length === 0 && (
        <div className="text-[13px] text-[var(--ds-gray-700)] text-center py-8">
          No tracks in queue
        </div>
      )}
    </div>
  );
}
