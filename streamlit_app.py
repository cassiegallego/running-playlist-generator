# --- FORM MODE ---
if mode == "Form":
    st.subheader("🏃 Build Your Workout")
    # ensure at least one step
    if not st.session_state.steps:
        st.session_state.steps = [{
            "step": "Warmup",
            "duration": 10,
            "hr_min": 100,
            "hr_max": 120
        }]
    # render each step
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
                value=s.get("duration", 10),
                key=f"dur_{i}"
            )
            # Safe HR Min/Max inputs
            new_hr_min = st.number_input(
                "HR ≥",
                min_value=40,
                max_value=200,
                value=s.get("hr_min", 60),
                key=f"hrmin_{i}"
            )
            old_hr_max = s.get("hr_max", new_hr_min)
            default_hr_max = max(old_hr_max, new_hr_min)
            new_hr_max = st.number_input(
                "HR ≤",
                min_value=new_hr_min,
                max_value=220,
                value=default_hr_max,
                key=f"hrmax_{i}"
            )
            s["hr_min"], s["hr_max"] = new_hr_min, new_hr_max

        with cols[1]:
            if st.button("📄 Copy", key=f"copy_{i}"):
                st.session_state.steps.insert(i+1, s.copy())
                st.experimental_rerun()

    # add/clear buttons
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
