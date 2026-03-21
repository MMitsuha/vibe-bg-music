"use client";
import { useState } from "react";
import useSWR from "swr";
import Navbar from "@/components/Navbar";
import PlaylistGrid from "@/components/PlaylistGrid";
import CategoryGrid from "@/components/CategoryGrid";
import PlayerBar from "@/components/PlayerBar";
import QueuePanel from "@/components/QueuePanel";
import { api } from "@/lib/api";

export default function Home() {
  const [queueVisible, setQueueVisible] = useState(false);
  const { data: catData, mutate: mutateCats } = useSWR("categories", api.categories);

  const hasCategories = catData && Object.keys(catData.categories).length > 0;

  return (
    <>
      <Navbar />
      <main className="max-w-[1100px] mx-auto px-6 py-12 pb-24">
        <PlaylistGrid onClassified={() => mutateCats()} />
        {hasCategories && (
          <>
            <hr className="border-t border-[var(--ds-gray-400)] my-0 mb-12" />
            <CategoryGrid />
          </>
        )}
      </main>
      <PlayerBar onToggleQueue={() => setQueueVisible((v) => !v)} />
      <QueuePanel visible={queueVisible} onClose={() => setQueueVisible(false)} />
    </>
  );
}
