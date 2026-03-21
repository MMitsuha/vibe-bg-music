import subprocess


class AppleMusicNotRunningError(Exception):
    pass


def _escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _run(script: str) -> str:
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode != 0:
        error = result.stderr.strip()
        if "not running" in error.lower() or "(-600)" in error:
            raise AppleMusicNotRunningError("Apple Music is not running")
        raise RuntimeError(f"osascript error: {error}")
    return result.stdout.strip()


def is_running() -> bool:
    script = 'tell application "System Events" to (name of processes) contains "Music"'
    return _run(script) == "true"


def _ensure_running():
    if not is_running():
        raise AppleMusicNotRunningError("Apple Music is not running")


def get_playlists() -> list[dict]:
    _ensure_running()
    script = '''
    tell application "Music"
        set output to ""
        repeat with p in user playlists
            set pName to name of p
            set pCount to count of tracks of p
            set output to output & pName & "|||" & pCount & "\\n"
        end repeat
        return output
    end tell
    '''
    raw = _run(script)
    playlists = []
    for line in raw.strip().split("\n"):
        if "|||" not in line:
            continue
        parts = line.split("|||")
        playlists.append({"name": parts[0], "track_count": int(parts[1])})
    return playlists


def get_tracks(playlist_name: str) -> list[dict]:
    _ensure_running()
    safe_name = _escape(playlist_name)
    script = f'''
    tell application "Music"
        set output to ""
        set theTracks to tracks of user playlist "{safe_name}"
        repeat with t in theTracks
            set tName to name of t
            set tArtist to artist of t
            set tAlbum to album of t
            set tDuration to duration of t
            set tID to database ID of t
            set output to output & tID & "|||" & tName & "|||" & tArtist & "|||" & tAlbum & "|||" & tDuration & "\\n"
        end repeat
        return output
    end tell
    '''
    raw = _run(script)
    tracks = []
    for line in raw.strip().split("\n"):
        if "|||" not in line:
            continue
        parts = line.split("|||")
        if len(parts) < 5:
            continue
        tracks.append({
            "database_id": int(parts[0]),
            "name": parts[1],
            "artist": parts[2],
            "album": parts[3],
            "duration": float(parts[4]),
        })
    return tracks


def play_track(playlist_name: str, database_id: int):
    _ensure_running()
    safe_name = _escape(playlist_name)
    script = f'''
    tell application "Music"
        set theTracks to (every track of user playlist "{safe_name}" whose database ID is {database_id})
        if (count of theTracks) > 0 then
            play item 1 of theTracks
        end if
    end tell
    '''
    _run(script)


def pause():
    _ensure_running()
    _run('tell application "Music" to pause')


def resume():
    _ensure_running()
    _run('tell application "Music" to play')


def next_track():
    _ensure_running()
    _run('tell application "Music" to next track')


def prev_track():
    _ensure_running()
    _run('tell application "Music" to previous track')


def get_player_state() -> dict:
    _ensure_running()
    script = '''
    tell application "Music"
        set pState to player state as string
        if pState is "stopped" then
            return "stopped|||||||0|||0|||stopped"
        end if
        set tName to name of current track
        set tArtist to artist of current track
        set tID to database ID of current track
        set tPos to player position
        set tDur to duration of current track
        return tName & "|||" & tArtist & "|||" & tID & "|||" & tPos & "|||" & tDur & "|||" & pState
    end tell
    '''
    raw = _run(script)
    parts = raw.split("|||")
    if len(parts) < 6:
        return {"name": "", "artist": "", "database_id": 0, "position": 0, "duration": 0, "state": "stopped"}
    return {
        "name": parts[0],
        "artist": parts[1],
        "database_id": int(parts[2]) if parts[2] else 0,
        "position": float(parts[3]) if parts[3] else 0,
        "duration": float(parts[4]) if parts[4] else 0,
        "state": parts[5].strip(),
    }


def set_position(seconds: float):
    _ensure_running()
    _run(f'tell application "Music" to set player position to {seconds}')


def get_volume() -> int:
    _ensure_running()
    return int(_run('tell application "Music" to get sound volume'))


def set_volume(level: int):
    _ensure_running()
    level = max(0, min(100, level))
    _run(f'tell application "Music" to set sound volume to {level}')
