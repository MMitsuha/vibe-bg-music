"use client";
import { useState } from "react";
import useSWR from "swr";
import { api } from "@/lib/api";

export default function PlaylistGrid({
  onClassified,
}: {
  onClassified: () => void;
}) {
  const { data, mutate } = useSWR("playlists", api.playlists);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [classifyStatus, setClassifyStatus] = useState<string>("idle");
  const [progress, setProgress] = useState("");

  const playlists = data?.playlists ?? [];
  const fillerCount = (3 - (playlists.length % 3)) % 3;

  function togglePlaylist(name: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  }

  async function handleClassify() {
    if (selected.size === 0 || classifyStatus === "classifying") return;
    setClassifyStatus("classifying");
    await api.classify([...selected]);

    const poll = setInterval(async () => {
      const s = await api.classifyStatus();
      setProgress(s.progress);
      if (s.status === "done") {
        clearInterval(poll);
        setClassifyStatus("done");
        onClassified();
      } else if (s.status === "error") {
        clearInterval(poll);
        setClassifyStatus("error");
      }
    }, 1000);
  }

  return (
    <section id="playlists">
      <h1 className="text-5xl font-extrabold tracking-[-0.04em] leading-tight mb-3">
        Select a Playlist
      </h1>
      <p className="text-base text-[var(--ds-gray-900)] mb-10 leading-relaxed">
        Choose a playlist from Apple Music, then classify tracks by genre with AI.
      </p>

      <div className="grid grid-cols-3 gap-px bg-[var(--ds-gray-400)] border border-[var(--ds-gray-400)] rounded-lg overflow-hidden mb-8">
        {playlists.map((p) => (
          <button
            key={p.name}
            onClick={() => togglePlaylist(p.name)}
            className={`relative bg-[var(--ds-background-100)] p-6 text-left transition-colors duration-150 hover:bg-[var(--ds-gray-100)] ${
              selected.has(p.name) ? "bg-[var(--ds-gray-100)]" : ""
            }`}
          >
            {selected.has(p.name) && (
              <span className="absolute top-3 right-3 w-2 h-2 rounded-full bg-[var(--geist-foreground)]" />
            )}
            <div className="text-sm font-semibold text-[var(--geist-foreground)]">{p.name}</div>
            <div className="text-[13px] text-[var(--ds-gray-700)]">{p.track_count} tracks</div>
          </button>
        ))}
        {Array.from({ length: fillerCount }).map((_, i) => (
          <div key={`filler-${i}`} className="bg-[var(--ds-background-100)]" />
        ))}
      </div>

      <div className="flex gap-3 mb-12">
        <button
          onClick={handleClassify}
          disabled={selected.size === 0 || classifyStatus === "classifying"}
          className="h-10 px-4 bg-[var(--geist-foreground)] text-[var(--geist-background)] rounded-lg text-sm font-medium transition-colors duration-150 hover:bg-[#ccc] disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {classifyStatus === "classifying" ? `Classifying... ${progress}` : "Classify with AI"}
        </button>
        <button
          onClick={() => mutate()}
          className="h-10 px-4 bg-transparent text-[var(--geist-foreground)] border border-[var(--ds-gray-400)] rounded-lg text-sm font-medium transition-all duration-150 hover:bg-[var(--ds-gray-alpha-200)] hover:border-[var(--geist-foreground)]"
        >
          Refresh Playlists
        </button>
      </div>
    </section>
  );
}
