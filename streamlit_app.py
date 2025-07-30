import streamlit as st
import requests
import base64
import math
import re

# --- Spotify Auth (same as before) ---
CLIENT_ID = st.secrets["SPOTIFY_CLIENT_ID"]
CLIENT_SECRET = st.secrets["SPOTIFY_CLIENT_SECRET"]

@st.cache_data(show_spinner=False)
def get_spotify_token():
    auth_url = "https://accounts.spotify.com/api/token"
    auth_header = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    resp = requests.post(auth_url,
                         headers={"Authorization": f"Basic {auth_header}"},
                         data={"grant_type": "client_credentials"})
    resp.raise_for_status()
    return resp.json()["access_token"]

token = get_spotify_token()
SP_HEADERS = {"Authorization": f"Bearer {token}"}

STEP_TYPES = [
    "Warmup","Recovery","Interval - Tempo","Interval - Threshold",
    "Interval - VO2max","Cooldown","Easy Run","Race"
]
DEFAULT_GENRES = [
    "pop","edm","hip-hop","rock","indie","country",
    "reggaeton","dancehall","instrumental","classical",
    "latin","lo-fi","house","jazz","afrobeat"
]

@st.cache_data(show_spinner=False)
def fetch_apple_link(track, artist):
    r = requests.get("https://itunes.apple.com/search",
                     params={"term":f"{track} {artist}", "media":"music", "limit":1})
    if r.ok and (res:=r.json().get("results")):
        return res[0].get("trackViewUrl")
    return None

st.title("🎵 Running Playlist Generator")

# Genre picker
genres = st.multiselect("Select genres:", DEFAULT_GENRES)
custom = st.text_input("Add custom genre:")
if custom:
    genres.append(custom.lower())

mode = st.radio("Enter workout via:", ["Form","Paste"])

# Initialize
if "steps" not in st.session_state:
    st.session_state.steps = []

# --- FORM MODE ---
if mode=="Form":
    st.subheader("🏃 Build Your Workout")
    # ensure at least one
    if not st.session_state.steps:
        st.session_state.steps = [{"step":"Warmup","duration":10,"hr_min":100,"hr_max":120,"pos":1}]
    # render each
    for i, s in enumerate(st.session_state.steps):
        st.markdown(f"**Step {i+1}**")
        s["step"] = st.selectbox("Type", STEP_TYPES, index=STEP_TYPES.index(s["step"]) if s["step"] in STEP_TYPES else 0, key=f"type{i}")
        s["duration"] = st.number_input("Duration (min)", min_value=1, max_value=300, value=s["duration"], key=f"dur{i}")
        s["hr_min"] = st.number_input("HR ≥", min_value=40, max_value=200, value=s["hr_min"], key=f"hrmin{i}")
        s["hr_max"] = st.number_input("HR ≤", min_value=s["hr_min"], max_value=220, value=s["hr_max"], key=f"hrmax{i}")
        s["pos"]    = st.number_input("Position (reorder)", min_value=1, max_value=100, value=s.get("pos", i+1), key=f"pos{i}")
        st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("➕ Add Step"):
            st.session_state.steps.append({"step":"","duration":1,"hr_min":60,"hr_max":100,"pos":len(st.session_state.steps)+1})
    with col2:
        if st.button("🗑️ Clear All"):
            st.session_state.steps.clear()

# --- PASTE MODE ---
else:
    st.subheader("📋 Paste Your Workout")
    text = st.text_area("Paste multi‑line workout (name, HR, duration):", height=300)
    if text:
        parsed=[]
        lines=[l.strip() for l in text.splitlines() if l.strip()]
        cur={}
        for l in lines:
            if re.match(r'^[A-Za-z].*$',l) and "hr" not in l.lower() and "min" not in l.lower():
                if all(k in cur for k in ("step","duration","hr_min","hr_max")):
                    parsed.append(cur)
                cur={"step":l}
            elif "hr" in l.lower():
                m=re.search(r'(\d+)\s*-\s*(\d+)',l)
                if m: cur.update({"hr_min":int(m.group(1)),"hr_max":int(m.group(2))})
            elif "min" in l.lower():
                m=re.search(r'(\d+)\s*min',l.lower())
                if m: cur["duration"]=int(m.group(1))
        if all(k in cur for k in ("step","duration","hr_min","hr_max")):
            parsed.append(cur)
        if parsed:
            # assign positions
            for idx,ps in enumerate(parsed):
                ps["pos"]=idx+1
            st.session_state.steps = parsed
            st.success(f"Parsed {len(parsed)} steps")
        else:
            st.warning("No valid steps found.")

# --- GENERATE ---
if st.session_state.steps and st.button("🎶 Generate Playlist"):
    # sort by position
    steps_sorted = sorted(st.session_state.steps, key=lambda x: x["pos"])
    st.subheader("📃 Your Playlist")
    for s in steps_sorted:
        st.markdown(f"**{s['step']}** — {s['duration']} min @ HR {s['hr_min']}–{s['hr_max']}")
        n = math.ceil(s["duration"]/3.5)
        resp = requests.get("https://api.spotify.com/v1/recommendations",
                            headers=SP_HEADERS,
                            params={"limit":n,
                                    "min_tempo":s["hr_min"],
                                    "max_tempo":s["hr_max"],
                                    "seed_genres":",".join(genres[:5])})
        tracks = resp.json().get("tracks",[])
        if not tracks:
            st.info("No tracks found for this step.")
        for t in tracks:
            title = t["name"]; artist = t["artists"][0]["name"]
            sp_url = t["external_urls"]["spotify"]; prev = t.get("preview_url")
            apple = fetch_apple_link(title, artist)
            line = f"- **{title}** by *{artist}*  \n[Spotify]({sp_url})"
            if prev: line += f" | [Preview]({prev})"
            if apple: line += f" | [Apple Music]({apple})"
            st.markdown(line)
    st.success("Done — enjoy your run! 🏃‍♀️🎵")
