"use client";
import { useState } from "react";
import useSWR from "swr";
import { api } from "@/lib/api";

export default function CategoryGrid() {
  const { data } = useSWR("categories", api.categories);
  const [customDesc, setCustomDesc] = useState("");
  const [customLoading, setCustomLoading] = useState(false);
  const [customError, setCustomError] = useState("");

  const categories = data?.categories ?? {};
  const playlistNames = data?.playlist_names ?? [];
  const entries = Object.entries(categories);

  // +1 for custom pick card
  const totalCards = entries.length + 1;
  const fillerCount = (3 - (totalCards % 3)) % 3;

  async function handleCustomPlay() {
    if (!customDesc.trim() || customLoading) return;
    setCustomLoading(true);
    setCustomError("");
    try {
      await api.playCustom(customDesc);
    } catch (e: unknown) {
      setCustomError(e instanceof Error ? e.message : "No matching tracks");
    } finally {
      setCustomLoading(false);
    }
  }

  if (entries.length === 0) return null;

  return (
    <section>
      <div className="flex items-baseline gap-3 mb-6" id="categories">
        <h2 className="text-2xl font-bold tracking-[-0.02em]">Categories</h2>
        {playlistNames.length > 0 && (
          <span className="text-sm text-[var(--ds-gray-700)]">from {playlistNames.join(", ")}</span>
        )}
      </div>

      <div className="grid grid-cols-3 gap-px bg-[var(--ds-gray-400)] border border-[var(--ds-gray-400)] rounded-lg overflow-hidden">
        {/* Custom Pick Card */}
        <div className="bg-[var(--ds-background-100)] p-6 flex flex-col gap-3">
          <div className="text-sm font-semibold text-[var(--geist-foreground)]">Custom Pick</div>
          <input
            type="text"
            value={customDesc}
            onChange={(e) => setCustomDesc(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleCustomPlay()}
            placeholder="Describe what you want to hear..."
            className="w-full px-3 py-2 bg-[var(--ds-background-100)] border border-[var(--ds-gray-400)] rounded-md text-[13px] text-[var(--geist-foreground)] placeholder:text-[var(--accents-3)] outline-none transition-colors duration-150 focus:border-[var(--geist-foreground)] font-[family-name:var(--font-geist-sans)]"
          />
          <button
            onClick={handleCustomPlay}
            disabled={customLoading || !customDesc.trim()}
            className="self-start px-3.5 py-1.5 bg-[var(--geist-foreground)] text-[var(--geist-background)] rounded-md text-[13px] font-medium transition-colors duration-150 hover:bg-[#ccc] disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {customLoading ? "Selecting..." : "Play matching tracks"}
          </button>
          {customError && (
            <span className="text-xs text-red-400">{customError}</span>
          )}
        </div>

        {/* Category Cards */}
        {entries.map(([name, tracks]) => (
          <button
            key={name}
            onClick={() => api.playCategory(name)}
            className="group bg-[var(--ds-background-100)] p-6 flex flex-col gap-1 text-left transition-colors duration-150 hover:bg-[var(--ds-gray-100)]"
          >
            <div className="text-sm font-semibold text-[var(--geist-foreground)]">{name}</div>
            <div className="text-[13px] text-[var(--ds-gray-700)]">{tracks.length} tracks</div>
            <div className="text-xs text-[var(--accents-3)] mt-2 opacity-0 group-hover:opacity-100 transition-opacity duration-150">
              Click to play &rarr;
            </div>
          </button>
        ))}

        {/* Filler Cards */}
        {Array.from({ length: fillerCount }).map((_, i) => (
          <div key={`filler-${i}`} className="bg-[var(--ds-background-100)]" />
        ))}
      </div>
    </section>
  );
}
