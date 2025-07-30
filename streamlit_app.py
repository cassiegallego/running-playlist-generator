import streamlit as st
import random

# --- Mock song database ---
# Replace or expand this with a real dataset or Spotify API later
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
    # Add more songs as needed
]

# --- HR Zone to BPM Map ---
ZONE_BPM_MAP = {
    "Z1-Z2": (120, 135),
    "Z3": (140, 160),
    "Z4": (160, 180),
    "Z5": (180, 200),
}

# --- Step Types for Dropdown ---
STEP_TYPES = [
    "Warmup", "Recovery", "Interval - Tempo", "Interval - Threshold",
    "Interval - VO2max", "Cooldown", "Easy Run", "Race"
]

# --- Genre options ---
DEFAULT_GENRES = [
    "Pop", "EDM", "Hip-Hop", "Rock", "Indie", "Country",
    "Reggaeton", "Dancehall", "Instrumental", "Classical",
    "Latin", "Lo-fi", "House", "Jazz", "Afrobeat"
]

# --- Streamlit App ---
st.title("🎵 Custom Running Playlist Generator")

st.markdown("Enter your workout steps and preferred music genres. We'll build a playlist that matches each step’s heart rate zone and duration.")

# --- Genre Selection ---
genres_selected = st.multiselect("Select your preferred music genres:", DEFAULT_GENRES)

custom_genre = st.text_input("Want to add a custom genre?")
if custom_genre:
    genres_selected.append(custom_genre)

# --- Workout Input ---
st.subheader("🏃‍♀️ Workout Steps")

steps = []
with st.form("workout_form"):
    num_steps = st.number_input("How many steps in your workout?", min_value=1, max_value=20, value=3)
    for i in range(int(num_steps)):
        st.markdown(f"### Step {i+1}")
        step_type = st.selectbox(f"Step {i+1} type:", STEP_TYPES, key=f"type_{i}")
        duration = st.number_input(f"Duration (in minutes)", min_value=1, max_value=180, key=f"duration_{i}")
        hr_min = st.number_input(f"HR Min", min_value=60, max_value=200, key=f"hr_min_{i}")
        hr_max = st.number_input(f"HR Max", min_value=hr_min, max_value=210, key=f"hr_max_{i}")
        steps.append({
            "step": step_type,
            "duration": duration,
            "hr_min": hr_min,
            "hr_max": hr_max
        })
    submitted = st.form_submit_button("Generate Playlist")

# --- Generate Playlist ---
if submitted:
    st.subheader("🎧 Your Step-Aligned Playlist")
    playlist = []
    for idx, step in enumerate(steps):
        st.markdown(f"#### {step['step']} ({step['duration']} min | HR: {step['hr_min']}-{step['hr_max']})")

        # Filter songs matching BPM and genres
        bpm_range = (step['hr_min'], step['hr_max'])
        candidates = [s for s in SONG_DB if
                      bpm_range[0] <= s["bpm"] <= bpm_range[1] and s["genre"] in genres_selected]

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

    st.success("Playlist complete! 🎶 Copy the links above to listen during your run.")

