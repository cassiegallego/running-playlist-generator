import streamlit as st
import requests
import base64
import math
import re
from streamlit_sortable import sortable  # pip install streamlit-sortable

# --- Spotify Auth omitted for brevity (same as v2) ---
CLIENT_ID = st.secrets["SPOTIFY_CLIENT_ID"]
CLIENT_SECRET = st.secrets["SPOTIFY_CLIENT_SECRET"]

@st.cache_data
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

STEP_TYPES = [
    "Warmup","Recovery","Interval - Tempo","Interval - Threshold",
    "Interval - VO2max","Cooldown","Easy Run","Race"
]
DEFAULT_GENRES = [
    "pop","edm","hip-hop","rock","indie","country",
    "reggaeton","dancehall","instrumental","classical",
    "latin","lo-fi","house","jazz","afrobeat"
]

def fetch_apple_link(track_name, artist_name):
    itunes_url = "https://itunes.apple.com/search"
    params = {"term": f"{track_name} {artist_name}", "media": "music", "limit": 1}
    r = requests.get(itunes_url, params=params)
    if r.ok and (res := r.json().get("results")):
        return res[0].get("trackViewUrl")
    return None

st.title("🎵 Running Playlist Generator (v2)")

# — Genre selector —
genres = st.multiselect("Select genres:", DEFAULT_GENRES)
custom = st.text_input("Add custom genre:")
if custom:
    genres.append(custom.lower())

mode = st.radio("Enter workout via:", ["Form","Paste"])

# — Initialize session_state for steps —
if "steps" not in st.session_state:
    st.session_state.steps = []

# — FORM MODE —
if mode == "Form":
    st.subheader("🏃 Build Your Workout")
    # Ensure there's at least one step
    if not st.session_state.steps:
        st.session_state.steps = [{"step": "", "duration": 1, "hr_min": 60, "hr_max": 120}]
    # Render each step's inputs
    for i, step in enumerate(st.session_state.steps):
        cols = st.columns((3, 1))
        with cols[0]:
            st.markdown(f"**Step {i+1}**")
            step["step"] = st.selectbox("Type", STEP_TYPES, index=STEP_TYPES.index(step["step"]) if step["step"] in STEP_TYPES else 0, key=f"type_{i}")
            step["duration"] = st.number_input("Duration (min)", min_value=1, max_value=300, value=step["duration"], key=f"dur_{i}")
            step["hr_min"] = st.number_input("HR ⩾", min_value=40, max_value=200, value=step["hr_min"], key=f"hrmin_{i}")
            step["hr_max"] = st.number_input("HR ⩽", min_value=step["hr_min"], max_value=220, value=step["hr_max"], key=f"hrmax_{i}")
        with cols[1]:
            if st.button("Copy", key=f"copy_{i}"):
                st.session_state.steps.insert(i+1, step.copy())
    # Buttons to add/remove steps
    col_add, col_clear = st.columns(2)
    with col_add:
        if st.button("➕ Add Step"):
            st.session_state.steps.append({"step": "", "duration": 1, "hr_min": 60, "hr_max": 120})
    with col_clear:
        if st.button("🗑️ Clear All"):
            st.session_state.steps = []

# — PASTE MODE —
else:
    st.subheader("📋 Paste Your Workout")
    text = st.text_area("Paste workout (multi‑line):", height=300)
    if text:
        # parse into session_state.steps
        parsed = []
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        cur = {}
        for l in lines:
            if re.match(r'^[A-Za-z].*$', l) and "hr" not in l.lower() and "min" not in l.lower():
                if all(k in cur for k in ("step","duration","hr_min","hr_max")):
                    parsed.append(cur)
                cur = {"step": l}
            elif "hr" in l.lower():
                m = re.search(r'(\d+)\s*-\s*(\d+)', l)
                if m: cur.update({"hr_min":int(m.group(1)),"hr_max":int(m.group(2))})
            elif "min" in l.lower():
                m = re.search(r'(\d+)\s*min', l.lower())
                if m: cur["duration"]=int(m.group(1))
        if all(k in cur for k in ("step","duration","hr_min","hr_max")):
            parsed.append(cur)
        if parsed:
            st.session_state.steps = parsed
            st.success(f"Parsed {len(parsed)} steps")
        else:
            st.warning("No valid steps parsed.")

# — If we have steps, allow reorder —
if st.session_state.steps:
    st.subheader("🔀 Reorder Your Steps (drag to rearrange)")
    labels = [
        f"{i+1}. {step['step']} — {step['duration']}m @ HR {step['hr_min']}-{step['hr_max']}"
        for i, step in enumerate(st.session_state.steps)
    ]
    new_labels = sortable(labels, key="reorder_steps")
    # apply new order
    reordered = []
    for lbl in new_labels:
        idx = int(lbl.split(".")[0]) - 1
        reordered.append(st.session_state.steps[idx])
    st.session_state.steps = reordered

# — Generate playlist —
if st.session_state.steps and st.button("🎶 Generate Playlist"):
    st.subheader("📃 Your Playlist")
    for s in st.session_state.steps:
        st.markdown(f"**{s['step']}** — {s['duration']} min @ HR {s['hr_min']}–{s['hr_max']}")
        n = math.ceil(s["duration"] / 3.5)
        # Spotify recommendations
        rec = requests.get(
            "https://api.spotify.com/v1/recommendations",
            headers=SPOTIFY_HEADERS,
            params={
                "limit": n,
                "min_tempo": s["hr_min"],
                "max_tempo": s["hr_max"],
                "seed_genres": ",".join(genres[:5])
            }
        ).json().get("tracks", [])
        if not rec:
            st.info("No tracks found for this step.")
        for t in rec:
            title = t["name"]; artist = t["artists"][0]["name"]
            sp = t["external_urls"]["spotify"]; prev = t.get("preview_url")
            apple = fetch_apple_link(title, artist)
            line = f"- **{title}** by *{artist}*  \n[Spotify]({sp})"
            if prev: line += f" | [Preview]({prev})"
            if apple: line += f" | [Apple Music]({apple})"
            st.markdown(line)
    st.success("Done! Enjoy your run. 🏃‍♀️🎵")
