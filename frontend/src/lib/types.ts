export interface Playlist {
  name: string;
  track_count: number;
}

export interface TrackSummary {
  database_id: number;
  name: string;
  artist: string;
  album: string;
  duration: number;
}

export interface PlayerStatus {
  name: string;
  artist: string;
  database_id: number;
  position: number;
  duration: number;
  state: string;
  volume: number;
  category: string | null;
  queue_length: number;
  queue_index: number;
}

export interface QueueData {
  queue: TrackSummary[];
  current_index: number;
}

export interface CategoriesData {
  playlist_names: string[];
  categories: Record<string, TrackSummary[]>;
}
