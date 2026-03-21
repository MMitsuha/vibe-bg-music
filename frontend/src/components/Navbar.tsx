"use client";
import useSWR from "swr";
import { api } from "@/lib/api";

export default function Navbar() {
  const { data } = useSWR("health", api.health, { refreshInterval: 5000 });
  const connected = data?.connected ?? false;

  return (
    <nav className="sticky top-0 z-50 flex items-center justify-between h-16 px-6 border-b border-[var(--ds-gray-400)] backdrop-blur-md backdrop-saturate-[1.8] bg-black/80">
      <div className="flex items-center gap-3">
        <span className="text-lg font-bold tracking-[-0.02em] text-[var(--geist-foreground)]">
          Vibe BG Music
        </span>
        <span className="text-2xl font-extralight text-[var(--accents-2)]">/</span>
        <div className="flex gap-6 ml-4">
          <a href="#playlists" className="text-sm text-[var(--geist-foreground)] hover:text-[var(--geist-foreground)] transition-colors duration-150">Playlists</a>
          <a href="#categories" className="text-sm text-[var(--ds-gray-900)] hover:text-[var(--geist-foreground)] transition-colors duration-150">Categories</a>
        </div>
      </div>
      <div className="flex items-center gap-2 text-[13px] text-[var(--ds-gray-900)]">
        <span
          className={`w-2 h-2 rounded-full ${connected ? "bg-green-500 animate-pulse" : "bg-red-500"}`}
        />
        {connected ? "Apple Music Connected" : "Disconnected"}
      </div>
    </nav>
  );
}
