"use client";
import { useState } from "react";
import Navbar from "@/components/Navbar";
import PlaylistGrid from "@/components/PlaylistGrid";
import CategoryGrid from "@/components/CategoryGrid";
import PlayerBar from "@/components/PlayerBar";
import QueuePanel from "@/components/QueuePanel";
import { mutate } from "swr";

export default function Home() {
  const [showCategories, setShowCategories] = useState(false);
  const [queueVisible, setQueueVisible] = useState(false);

  function handleClassified() {
    setShowCategories(true);
    mutate("categories");
  }

  return (
    <>
      <Navbar />
      <main className="max-w-[1100px] mx-auto px-6 py-12 pb-24">
        <PlaylistGrid onClassified={handleClassified} />
        {showCategories && (
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
