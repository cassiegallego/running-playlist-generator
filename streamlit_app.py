import streamlit as st
import requests
import base64
import math
import re

# --- Spotify API Auth (Client Credentials Flow) ---
CLIENT_ID = st.secrets["SPOTIFY_CLIENT_ID"]
CLIENT_SECRET = st.secrets["SPOTIFY_CLIENT_SECRET"]

@st.cache_data(show_spinner=False)
def get_spotify_token():
    auth_url = "https://accounts.spotify.com/api/token"
    auth_header = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    headers = {"Authorization": f"Basic {auth_header}"}
    data = {"grant_type": "client_credentials"}
    resp = requests.post(auth_url, headers=headers, data=data)
    resp.raise_for_status()
    return resp.json()["access_token"]

token = get_spotify_token()
SPOTIFY_HEADERS = {"Authorization": f"Bearer {token}"}

# --- Constants ---
STEP_TYPES = [
    "Warmup", "Recovery", "Interval - Tempo", "Interval - Threshold",
    "Interval - VO2max", "Cooldown", "Easy Run", "Race"
]
DEFAULT_GENRES = [
    "pop", "edm", "hip-hop", "rock", "indie", "country",
    "reggaeton", "dancehall", "instrumental", "classical",
    "latin", "lo-fi", "house", "jazz", "afrobeat"
]

# --- Helper: iTunes Search for Apple Music Link ---
@st.cache_data(show_spinner=False)
def fetch_apple_link(track_name, artist_name):
    itunes_url = "https://itunes.apple.com/search"
    params = {
        "term": f"{track_name} {artist_name}",
        "media": "music",
        "limit": 1,
    }
    r = requests.get(itunes_url, params=params)
    if r.ok:
        results = r.json().get("results")
        if results:
            return results[0].get("trackViewUrl")
    return None

# --- Streamlit UI ---
st.title("🎵 Running Playlist Generator (v2)")

# Genres
genres = st.multiselect("Select genres:", DEFAULT_GENRES)
custom = st.text_input("Add custom genre (Spotify may or may not support it):")
if custom:
    genres.append(custom.lower())

# Mode
mode = st.radio("Enter workout via:", ["Form", "Paste"])
steps = []

# Form Mode
if mode == "Form":
    if "n_steps" not in st.session_state:
        st.session_state.n_steps = 1

    st.subheader("🏃 Build Your Workout")
    for i in range(st.session_state.n_steps):
        st.markdown(f"**Step {i+1}**")
        step = st.selectbox(f"Type:", STEP_TYPES, key=f"type{i}")
        dur = st.number_input("Duration (min):", min_value=1, max_value=300, key=f"dur{i}")
        hr_min = st.number_input("HR ⩾", min_value=40, max_value=200, key=f"hrmin{i}")
        hr_max = st.number_input("HR ⩽", min_value=hr_min, max_value=220, key=f"hrmax{i}")
        steps.append({"step": step, "duration": dur, "hr_min": hr_min, "hr_max": hr_max})
    if st.button("➕ Add another step"):
        st.session_state.n_steps += 1

# Paste Mode
else:
    st.subheader("📋 Paste Your Workout")
    text = st.text_area("E.g.:\n\nWarm up\nHR 112 - 150 bpm\n10 min\n\nInterval - Tempo\nHR 154 - 165 bpm\n4 min\n…")
    if text:
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        cur = {}
        for l in lines:
            # Step name
            if re.match(r'^[A-Za-z].*$', l) and "hr" not in l.lower() and "min" not in l.lower():
                if all(k in cur for k in ("step","duration","hr_min","hr_max")):
                    steps.append(cur)
                cur = {"step": l}
            # HR line
            elif "hr" in l.lower():
                m = re.search(r'(\d+)\s*-\s*(\d+)', l)
                if m:
                    cur["hr_min"], cur["hr_max"] = int(m.group(1)), int(m.group(2))
            # Duration line
            elif "min" in l.lower():
                m = re.search(r'(\d+)\s*min', l.lower())
                if m:
                    cur["duration"] = int(m.group(1))
        if all(k in cur for k in ("step","duration","hr_min","hr_max")):
            steps.append(cur)
        if not steps:
            st.warning("Couldn't parse any steps—check formatting.")

# Generate Playlist
if steps and st.button("🎶 Generate Playlist"):
    st.subheader("📃 Your Playlist")

    for s in steps:
        st.markdown(f"**{s['step']}** — {s['duration']} min @ HR {s['hr_min']}–{s['hr_max']}")
        # Estimate # tracks
        n = math.ceil(s["duration"] / 3.5)

        # Build Recommendation query
        rec_url = "https://api.spotify.com/v1/recommendations"
        params = {
            "limit": n,
            "min_tempo": s["hr_min"],
            "max_tempo": s["hr_max"],
            "seed_genres": ",".join(genres[:5])  # max 5 seeds
        }
        r = requests.get(rec_url, headers=SPOTIFY_HEADERS, params=params)
        if not r.ok:
            st.error(f"Spotify error: {r.text}")
            continue

        tracks = r.json().get("tracks", [])
        if not tracks:
            st.info("No tracks found for these parameters.")
            continue

        for t in tracks:
            title = t["name"]
            artist = t["artists"][0]["name"]
            spotify_url = t["external_urls"]["spotify"]
            preview = t.get("preview_url")
            apple = fetch_apple_link(title, artist)

            line = f"- **{title}** by *{artist}*  \n"
            line += f"[Spotify]({spotify_url})"
            if preview:
                line += f" | [Preview]({preview})"
            if apple:
                line += f" | [Apple Music]({apple})"
            st.markdown(line)

    st.success("Done! Enjoy your run. 🏃‍♀️🎵")
