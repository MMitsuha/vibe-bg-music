import type { CategoriesData, PlayerStatus, Playlist, QueueData } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

export const api = {
  health: () => request<{ connected: boolean }>("/api/health"),
  playlists: () => request<{ playlists: Playlist[] }>("/api/playlists"),

  classify: (playlists: string[]) =>
    request<{ status: string }>("/api/classify", {
      method: "POST",
      body: JSON.stringify({ playlists }),
    }),
  classifyStatus: () => request<{ status: string; progress: string }>("/api/classify/status"),
  categories: () => request<CategoriesData>("/api/categories"),

  playCategory: (name: string) =>
    request<{ playing: string }>(`/api/play/category/${encodeURIComponent(name)}`, { method: "POST" }),
  playCustom: (description: string) =>
    request<{ playing: string; matched_count: number }>("/api/play/custom", {
      method: "POST",
      body: JSON.stringify({ description }),
    }),

  control: (action: string) =>
    request("/api/player/control", { method: "POST", body: JSON.stringify({ action }) }),
  status: () => request<PlayerStatus>("/api/player/status"),
  artwork: (databaseId: number) => `${API_BASE}/api/player/artwork?t=${databaseId}`,
  setVolume: (volume: number) =>
    request("/api/player/volume", { method: "POST", body: JSON.stringify({ volume }) }),
  seek: (position: number) =>
    request("/api/player/seek", { method: "POST", body: JSON.stringify({ position }) }),

  queue: () => request<QueueData>("/api/player/queue"),
  removeFromQueue: (index: number) => request(`/api/player/queue/${index}`, { method: "DELETE" }),
  jumpTo: (index: number) => request(`/api/player/jump/${index}`, { method: "POST" }),
};
