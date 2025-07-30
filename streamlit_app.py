import streamlit as st
import requests
import base64
import math
import re
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

# --- Spotify Auth (Client Credentials Flow) ---
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
SP_HEADERS = {"Authorization": f"Bearer {token}"}

# --- iTunes Search for Apple Music Link ---
@st.cache_data(show_spinner=False)
def fetch_apple_link(track, artist):
    itunes_url = "https://itunes.apple.com/search"
    params = {"term": f"{track} {artist}", "media": "music", "limit": 1}
    resp = requests.get(itunes_url, params=params)
    if resp.ok:
        results = resp.json().get("results")
        if results:
            return results[0].get("trackViewUrl")
    return None

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

# --- UI: Title + Genre Selection + Mode Toggle ---
st.title("🎵 Running Playlist Generator")
genres = st.multiselect("Select genres:", DEFAULT_GENRES)
custom = st.text_input("Add custom genre:")
if custom:
    genres.append(custom.lower())

mode = st.radio("Enter workout via:", ["Form", "Paste"])

# --- Initialize steps in session_state ---
if "steps" not in st.session_state:
    st.session_state.steps = []

# --- FORM MODE ---
if mode == "Form":
    st.subheader("🏃 Build Your Workout Steps")
    # Ensure at least one step
    if not st.session_state.steps:
        st.session_state.steps = [{
            "step": "Warmup",
            "duration": 10,
            "hr_min": 100,
            "hr_max": 120
        }]
    # Render each step with Copy button
    for i, s in enumerate(st.session_state.steps):
        cols = st.columns([3, 1])
        with cols[0]:
            s["step"] = st.selectbox(
                "Type",
                STEP_TYPES,
                index=STEP_TYPES.index(s["step"]) if s["step"] in STEP_TYPES else 0,
                key=f"type_{i}"
            )
            s["duration"] = st.number_input(
                "Duration (min)",
                min_value=1,
                max_value=300,
                value=s["duration"],
                key=f"dur_{i}"
            )
            s["hr_min"] = st.number_input(
                "HR ≥",
                min_value=40,
                max_value=200,
                value=s["hr_min"],
                key=f"hrmin_{i}"
            )
            s["hr_max"] = st.number_input(
                "HR ≤",
                min_value=s["hr_min"],
                max_value=220,
                value=s["hr_max"],
                key=f"hrmax_{i}"
            )
        with cols[1]:
            if st.button("📄 Copy", key=f"copy_{i}"):
                st.session_state.steps.insert(i+1, s.copy())
                st.experimental_rerun()

    # Add / Clear buttons
    c1, c2 = st.columns(2)
    with c1:
        if st.button("➕ Add Blank Step"):
            st.session_state.steps.append({
                "step": "",
                "duration": 5,
                "hr_min": 60,
                "hr_max": 100
            })
    with c2:
        if st.button("🗑️ Clear All Steps"):
            st.session_state.steps.clear()

# --- PASTE MODE ---
else:
    st.subheader("📋 Paste Your Workout")
    text = st.text_area(
        "Paste multi-line steps (Name / HR Min‑Max / Duration):",
        height=300
    )
    if text:
        parsed = []
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        cur = {}
        for ln in lines:
            # Step name
            if re.match(r'^[A-Za-z].*$', ln) and "hr" not in ln.lower() and "min" not in ln.lower():
                if all(k in cur for k in ("step", "duration", "hr_min", "hr_max")):
                    parsed.append(cur)
                cur = {"step": ln}
            # HR line
            elif "hr" in ln.lower():
                m = re.search(r'(\d+)\s*-\s*(\d+)', ln)
                if m:
                    cur["hr_min"], cur["hr_max"] = int(m.group(1)), int(m.group(2))
            # Duration line
            elif "min" in ln.lower():
                m = re.search(r'(\d+)\s*min', ln.lower())
                if m:
                    cur["duration"] = int(m.group(1))
        if all(k in cur for k in ("step", "duration", "hr_min", "hr_max")):
            parsed.append(cur)

        if parsed:
            st.session_state.steps = parsed
            st.success(f"Parsed {len(parsed)} steps")
        else:
            st.warning("No valid steps parsed. Check your formatting.")

# --- DRAG‑AND‑DROP GRID for Reordering & Editing ---
if st.session_state.steps:
    st.subheader("🔀 Reorder & Edit Your Steps")
    df = pd.DataFrame(st.session_state.steps)
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_grid_options(rowDragManaged=True, animateRows=True)
    gb.configure_selection("single")
    grid_opts = gb.build()
    grid_response = AgGrid(
        df,
        gridOptions=grid_opts,
        update_mode=GridUpdateMode.MANUAL,
        allow_unsafe_jscode=True,
        height=300,
        fit_columns_on_grid_load=True,
    )
    st.session_state.steps = pd.DataFrame(grid_response["data"]).to_dict("records")

# --- Generate Playlist ---
if st.session_state.steps and st.button("🎶 Generate Playlist"):
    st.subheader("📃 Your Playlist")
    for s in st.session_state.steps:
        st.markdown(f"**{s['step']}** — {s['duration']} min @ HR {s['hr_min']}–{s['hr_max']}")
        n_tracks = math.ceil(s["duration"] / 3.5)

        # Spotify Recommendations
        resp = requests.get(
            "https://api.spotify.com/v1/recommendations",
            headers=SP_HEADERS,
            params={
                "limit": n_tracks,
                "min_tempo": s["hr_min"],
                "max_tempo": s["hr_max"],
                "seed_genres": ",".join(genres[:5])
            },
        )
        if not resp.ok:
            st.error("Spotify error.")
            break

        for t in resp.json().get("tracks", []):
            title = t["name"]
            artist = t["artists"][0]["name"]
            sp_url = t["external_urls"]["spotify"]
            preview = t.get("preview_url")
            apple = fetch_apple_link(title, artist)

            line = f"- **{title}** by *{artist}*  \n[Spotify]({sp_url})"
            if preview:
                line += f" | [Preview]({preview})"
            if apple:
                line += f" | [Apple Music]({apple})"
            st.markdown(line)

    st.success("Done! Enjoy your run. 🏃‍♀️🎵")
