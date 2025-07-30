import streamlit as st
import random

# --- Song database (mock) ---
SONG_DB = [
    {"title": "Lose Yourself", "artist": "Eminem", "bpm": 171, "genre": "Hip-Hop", "duration": 4.5,
     "spotify": "https://open.spotify.com/track/1", "apple": "https://music.apple.com/track/1"},
    {"title": "Blinding Lights", "artist": "The Weeknd", "bpm": 173, "genre": "Pop", "duration": 3.2,
     "spotify": "https://open.spotify.com/track/2", "apple": "https://music.apple.com/track/2"},
    {"title": "Sandstorm", "artist": "Darude", "bpm": 136, "genre": "EDM", "duration": 3.8,
     "spotify": "https://open.spotify.com/track/3", "apple": "https://music.apple.com/track/3"},
    {"title": "Levels", "artist": "Avicii", "bpm": 126, "genre": "EDM", "duration": 5.0,
     "spotify": "https://open.spotify.com/track/4", "apple": "https://music.apple.com/track/4"},
    {"title": "HUMBLE.", "artist": "Kendrick Lamar", "bpm": 150, "genre": "Hip-Hop", "duration": 2.9,
     "spotify": "https://open.spotify.com/track/5", "apple": "https://music.apple.com/track/5"},
]

STEP_TYPES = [
    "Warmup", "Recovery", "Interval - Tempo", "Interval - Threshold",
    "Interval - VO2max", "Cooldown", "Easy Run", "Race"
]

DEFAULT_GENRES = [
    "Pop", "EDM", "Hip-Hop", "Rock", "Indie", "Country",
    "Reggaeton", "Dancehall", "Instrumental", "Classical",
    "Latin", "Lo-fi", "House", "Jazz", "Afrobeat"
]

# --- App Title ---
st.title("🎧 Custom Running Playlist Generator")

# --- Genre Selection ---
genres_selected = st.multiselect("Select your preferred music genres:", DEFAULT_GENRES)
custom_genre = st.text_input("Want to add a custom genre?")
if custom_genre:
    genres_selected.append(custom_genre)

# --- Mode Toggle ---
mode = st.radio("How would you like to enter your workout?", ["Form", "Paste"])

steps = []

# --- FORM MODE ---
if mode == "Form":
    if "step_count" not in st.session_state:
        st.session_state.step_count = 1

    st.subheader("🏃 Workout Steps")
    for i in range(st.session_state.step_count):
        st.markdown(f"### Step {i + 1}")
        step_type = st.selectbox(f"Step {i + 1} type:", STEP_TYPES, key=f"type_{i}")
        duration = st.number_input(f"Duration (min)", min_value=1, max_value=180, key=f"duration_{i}")
        hr_min = st.number_input(f"HR Min", min_value=60, max_value=200, key=f"hr_min_{i}")
        hr_max = st.number_input(f"HR Max", min_value=hr_min, max_value=210, key=f"hr_max_{i}")
        steps.append({
            "step": step_type,
            "duration": duration,
            "hr_min": hr_min,
            "hr_max": hr_max
        })

    if st.button("➕ Add another step"):
        st.session_state.step_count += 1

# --- PASTE MODE ---
elif mode == "Paste":
    st.subheader("📋 Paste Your Workout Steps")
    pasted_text = st.text_area("Paste your workout steps here (format: Step Type – Duration – HR Min–Max):", height=200)

    if pasted_text:
        for line in pasted_text.splitlines():
            try:
                parts = [p.strip() for p in line.split("–")]
                step = parts[0]
                duration = int(parts[1].split()[0])
                hr_range = [int(n) for n in parts[2].replace("HR", "").strip().split("–")]
                steps.append({
                    "step": step,
                    "duration": duration,
                    "hr_min": hr_range[0],
                    "hr_max": hr_range[1]
                })
            except Exception as e:
                st.error(f"Error parsing line: `{line}` – {e}")

# --- Playlist Generator ---
if steps and st.button("🎵 Generate Playlist"):
    st.subheader("📃 Playlist")
    playlist = []
    for idx, step in enumerate(steps):
        st.markdown(f"#### {step['step']} ({step['duration']} min | HR: {step['hr_min']}-{step['hr_max']})")
        bpm_range = (step["hr_min"], step["hr_max"])
        candidates = [s for s in SONG_DB if bpm_range[0] <= s["bpm"] <= bpm_range[1] and s["genre"] in genres_selected]

        total_time = 0
        step_playlist = []
        while total_time < step["duration"] and candidates:
            song = random.choice(candidates)
            if total_time + song["duration"] > step["duration"] + 0.5:
                break
            step_playlist.append(song)
            total_time += song["duration"]
            playlist.append(song)

        for song in step_playlist:
            st.markdown(f"- **{song['title']}** by *{song['artist']}*  \n"
                        f"[Spotify]({song['spotify']}) | [Apple Music]({song['apple']})")

    st.success("Playlist created! 🎶 Copy the links to listen during your workout.")
