import streamlit as st
import ephem
import datetime
import math
import pytz
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai

# --- PAGE CONFIG (Mobile Friendly) ---
st.set_page_config(page_title="Vedic Matcher Pro", page_icon="🕉️", layout="centered")

# --- CSS FOR MOBILE CARDS ---
st.markdown("""
<style>
    .guna-card {
        background-color: #f0f2f6;
        color: #31333F; 
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
        border-left: 5px solid #ccc;
    }
    .guna-header {
        font-size: 18px;
        font-weight: bold;
        display: flex;
        justify-content: space-between;
        color: #31333F;
    }
    .guna-score { font-weight: bold; }
    .guna-reason { font-size: 14px; color: #555; margin-top: 5px; font-style: italic; }
    
    .border-red { border-left-color: #ff4b4b !important; }
    .border-orange { border-left-color: #ffa500 !important; }
    .border-green { border-left-color: #00cc00 !important; }
    
    .text-red { color: #ff4b4b !important; }
    .text-orange { color: #ffa500 !important; }
    .text-green { color: #00cc00 !important; }
</style>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
if "calculated" not in st.session_state: st.session_state.calculated = False
if "results" not in st.session_state: st.session_state.results = {}
if "input_mode" not in st.session_state: st.session_state.input_mode = "Birth Details"

# --- DATA ---
NAKSHATRAS = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra","Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni","Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha","Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta","Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"]
RASHIS = ["Aries (Mesha)", "Taurus (Vrishabha)", "Gemini (Mithuna)", "Cancer (Karka)","Leo (Simha)", "Virgo (Kanya)", "Libra (Tula)", "Scorpio (Vrishchika)","Sagittarius (Dhanu)", "Capricorn (Makara)", "Aquarius (Kumbha)", "Pisces (Meena)"]
NAK_TO_RASHI_MAP = {0: [0], 1: [0], 2: [0, 1], 3: [1], 4: [1, 2], 5: [2], 6: [2, 3], 7: [3], 8: [3], 9: [4], 10: [4], 11: [4, 5], 12: [5], 13: [5, 6], 14: [6], 15: [6, 7], 16: [7], 17: [7], 18: [8], 19: [8], 20: [8, 9], 21: [9], 22: [9, 10], 23: [10], 24: [10, 11], 25: [11], 26: [11]}
SUN_TRANSIT_DATES = {0: "Apr 14 - May 14", 1: "May 15 - Jun 14", 2: "Jun 15 - Jul 15", 3: "Jul 16 - Aug 16", 4: "Aug 17 - Sep 16", 5: "Sep 17 - Oct 16", 6: "Oct 17 - Nov 15", 7: "Nov 16 - Dec 15", 8: "Dec 16 - Jan 13", 9: "Jan 14 - Feb 12", 10: "Feb 13 - Mar 13", 11: "Mar 14 - Apr 13"}
VARNA_GROUP = [0, 1, 2, 0, 1, 2, 2, 0, 1, 2, 2, 0]
VASHYA_GROUP = [0, 0, 1, 2, 1, 1, 1, 3, 1, 2, 1, 2]
YONI_ID = [0, 1, 2, 3, 3, 4, 5, 2, 5, 6, 6, 7, 8, 9, 8, 9, 10, 10, 4, 11, 12, 11, 13, 0, 13, 7, 1]
YONI_Enemy_Map = {0:8, 1:13, 2:11, 3:12, 4:10, 5:6, 6:5, 7:9, 8:0, 9:7, 10:4, 11:2, 12:3, 13:1}
RASHI_LORDS = [2, 5, 3, 1, 0, 3, 5, 2, 4, 6, 6, 4] 
MAITRI_TABLE = [[5, 5, 5, 4, 5, 0, 0], [5, 5, 4, 1, 4, 1, 1], [5, 4, 5, 0.5, 5, 3, 0.5],[4, 1, 0.5, 5, 0.5, 5, 4], [5, 4, 5, 0.5, 5, 0.5, 3], [0, 1, 3, 5, 0.5, 5, 5], [0, 1, 0.5, 4, 3, 5, 5]]
GANA_TYPE = [0, 1, 2, 1, 0, 1, 0, 0, 2, 2, 1, 1, 0, 2, 0, 2, 0, 2, 2, 1, 1, 0, 2, 2, 1, 1, 0]
NADI_TYPE = [0, 1, 2, 2, 1, 0, 0, 1, 2, 0, 1, 2, 2, 1, 0, 0, 1, 2, 0, 1, 2, 2, 1, 0, 0, 1, 2]
SAME_NAKSHATRA_ALLOWED = ["Rohini", "Ardra", "Pushya", "Magha", "Vishakha", "Shravana", "Uttara Bhadrapada", "Revati"]
NAK_TRAITS = {0: {"Trait": "Pioneer"}, 1: {"Trait": "Creative"}, 2: {"Trait": "Sharp"}, 3: {"Trait": "Sensual"}, 4: {"Trait": "Curious"}, 5: {"Trait": "Intellectual"}, 6: {"Trait": "Nurturing"}, 7: {"Trait": "Spiritual"}, 8: {"Trait": "Mystical"}, 9: {"Trait": "Royal"}, 10: {"Trait": "Social"}, 11: {"Trait": "Charitable"}, 12: {"Trait": "Skilled"}, 13: {"Trait": "Beautiful"}, 14: {"Trait": "Independent"}, 15: {"Trait": "Focused"}, 16: {"Trait": "Friendship"}, 17: {"Trait": "Protective"}, 18: {"Trait": "Deep"}, 19: {"Trait": "Invincible"}, 20: {"Trait": "Victory"}, 21: {"Trait": "Listener"}, 22: {"Trait": "Musical"}, 23: {"Trait": "Healer"}, 24: {"Trait": "Passionate"}, 25: {"Trait": "Ascetic"}, 26: {"Trait": "Complete"}}

@st.cache_resource
def get_geolocator(): return Nominatim(user_agent="vedic_matcher_v31_final", timeout=10)
@st.cache_resource
def get_tf(): return TimezoneFinder()
@st.cache_data(ttl=3600)
def get_cached_coords(city, country):
    try: return get_geolocator().geocode(f"{city}, {country}")
    except: return None

def get_offset_smart(city, country, dt, manual_tz):
    tf = get_tf(); loc = get_cached_coords(city, country)
    try:
        if loc:
            tz = pytz.timezone(tf.timezone_at(lng=loc.longitude, lat=loc.latitude))
            return tz.localize(dt).utcoffset().total_seconds()/3600.0, f"📍 {city}"
        raise ValueError
    except: return manual_tz, f"⚠️ Manual TZ"

def get_planetary_positions(date_obj, time_obj, city, country):
    dt = datetime.datetime.combine(date_obj, time_obj)
    offset, msg = get_offset_smart(city, country, dt, 5.5)
    obs = ephem.Observer(); obs.date = dt - datetime.timedelta(hours=offset)
    obs.lat, obs.lon = '28.6139', '77.2090' 
    if city: 
        loc = get_cached_coords(city, country)
        if loc: obs.lat, obs.lon = str(loc.latitude), str(loc.longitude)
    
    moon = ephem.Moon(); moon.compute(obs)
    mars = ephem.Mars(); mars.compute(obs)
    sun = ephem.Sun(); sun.compute(obs)
    
    ayanamsa = 23.85 + (dt.year - 2000) * 0.01396
    s_moon = (math.degrees(ephem.Ecliptic(moon).lon) - ayanamsa) % 360
    s_mars = (math.degrees(ephem.Ecliptic(mars).lon) - ayanamsa) % 360
    s_sun = (math.degrees(ephem.Ecliptic(sun).lon) - ayanamsa) % 360
    return s_moon, s_mars, s_sun, msg

def get_nak_rashi(long): return int(long / 13.333333), int(long / 30)

def check_mars_dosha_smart(moon_rashi, mars_long):
    mars_rashi = int(mars_long / 30)
    house_diff = (mars_rashi - moon_rashi) % 12 + 1
    is_dosha_house = house_diff in [2, 4, 7, 8, 12]
    status = "Safe"
    if is_dosha_house:
        if mars_rashi == 0 or mars_rashi == 7: status = f"Neutralized (Mars in Own Sign - House {house_diff})"
        elif mars_rashi == 9: status = f"Neutralized (Mars Exalted - House {house_diff})"
        else: return True, f"⚠️ Dosha Present (House {house_diff})"
    return False, status

def get_jupiter_position_for_year(year):
    dt = datetime.date(year, 7, 1); obs = ephem.Observer(); obs.date = dt
    jupiter = ephem.Jupiter(); jupiter.compute(obs); ecl = ephem.Ecliptic(jupiter)
    ayanamsa = 23.85 + (year - 2000) * 0.01396
    return int(((math.degrees(ecl.lon) - ayanamsa) % 360) / 30)

def predict_marriage_luck_years(rashi_idx):
    predictions = []
    for year in [2025, 2026, 2027]:
        jup_rashi = get_jupiter_position_for_year(year)
        house = (jup_rashi - rashi_idx) % 12 + 1
        res = "✨ Excellent" if house in [2, 5, 7, 9, 11] else "Neutral"
        predictions.append((year, res))
    return predictions

def predict_wedding_month(rashi_idx): return SUN_TRANSIT_DATES[(rashi_idx + 6) % 12]

# --- CORE CALCULATION ENGINE ---
def calculate_all(b_nak, b_rashi, g_nak, g_rashi):
    maitri_raw = MAITRI_TABLE[RASHI_LORDS[b_rashi]][RASHI_LORDS[g_rashi]]
    friends = maitri_raw >= 4
    score = 0; bd = []; logs = []
    
    # 1. Varna
    v_raw = 1 if VARNA_GROUP[b_rashi] <= VARNA_GROUP[g_rashi] else 0
    v_final = v_raw; reason = "Natural Match" if v_raw == 1 else "Mismatch"
    if v_raw == 0 and friends: 
        v_final = 1; reason = "Boosted by Maitri"; logs.append("Varna: Boosted by Maitri")
    score += v_final; bd.append(("Varna", v_raw, v_final, 1, reason))
    
    # 2. Vashya
    va_raw = 0
    if VASHYA_GROUP[b_rashi] == VASHYA_GROUP[g_rashi]: va_raw = 2
    elif (VASHYA_GROUP[b_rashi] == 0 and VASHYA_GROUP[g_rashi] == 1) or (VASHYA_GROUP[b_rashi] == 1 and VASHYA_GROUP[g_rashi] == 0): va_raw = 1 
    elif VASHYA_GROUP[b_rashi] != VASHYA_GROUP[g_rashi]: va_raw = 0.5 
    va_final = va_raw; reason = "Magnetic" if va_raw >= 1 else "Mismatch"
    if va_raw < 2 and (friends or YONI_ID[b_nak]==YONI_ID[g_nak]): 
        va_final = 2; reason = "Boosted by Maitri/Yoni"; logs.append("Vashya: Boosted by Maitri/Yoni")
    score += va_final; bd.append(("Vashya", va_raw, va_final, 2, reason))
    
    # 3. Tara
    cnt = (b_nak - g_nak)%27 + 1
    t_raw = 3 if cnt%9 not in [3,5,7] else 0
    t_final = t_raw; reason = "Benefic" if t_raw == 3 else "Malefic"
    if t_raw == 0 and friends: 
        t_final = 3; reason = "Boosted by Maitri"; logs.append("Tara: Boosted by Maitri")
    score += t_final; bd.append(("Tara", t_raw, t_final, 3, reason))
    
    # 4. Yoni
    y_raw = 4 if YONI_ID[b_nak] == YONI_ID[g_nak] else (0 if YONI_Enemy_Map.get(YONI_ID[b_nak]) == YONI_ID[g_nak] else 2)
    y_final = y_raw; reason = "Perfect" if y_raw == 4 else "Mismatch"
    if y_raw < 4 and (friends or va_final>=1): 
        y_final = 4; reason = "Compensated by Maitri/Vashya"; logs.append("Yoni: Compensated by Maitri/Vashya")
    score += y_final; bd.append(("Yoni", y_raw, y_final, 4, reason))
    
    # 5. Maitri
    m_final = maitri_raw
    score += m_final; bd.append(("Maitri", maitri_raw, m_final, 5, "Friendly" if m_final>=4 else "Enemy"))
    
    # 6. Gana
    gb, gg = GANA_TYPE[b_nak], GANA_TYPE[g_nak]
    ga_raw = 6 if gb==gg else (0 if (gg==1 and gb==2) or (gg==2 and gb==1) else 1)
    ga_final = ga_raw; reason = "Match" if ga_raw >= 5 else "Mismatch"
    if ga_raw < 6 and friends: 
        ga_final = 6; reason = "Boosted by Maitri"; logs.append("Gana: Boosted by Maitri")
    score += ga_final; bd.append(("Gana", ga_raw, ga_final, 6, reason))
    
    # 7. Bhakoot
    dist = (b_rashi-g_rashi)%12
    bh_raw = 7 if dist not in [1,11,4,8,5,7] else 0
    bh_final = bh_raw; reason = "Love Flow" if bh_raw == 7 else "Blocked"
    if bh_raw == 0 and (friends or NADI_TYPE[b_nak]!=NADI_TYPE[g_nak]): 
        bh_final = 7; reason = "Compensated by Maitri/Nadi"; logs.append("Bhakoot: Compensated")
    score += bh_final; bd.append(("Bhakoot", bh_raw, bh_final, 7, reason))
    
    # 8. Nadi
    n_raw = 8; n_final = 8; n_reason = "Healthy"
    if NADI_TYPE[b_nak] == NADI_TYPE[g_nak]:
        n_raw = 0; n_final = 0; n_reason = "Same Nadi (Dosha)"
        if b_nak==g_nak and NAKSHATRAS[b_nak] in SAME_NAKSHATRA_ALLOWED: n_final=8; n_reason="Exception: Allowed Star"; logs.append("Nadi: Star Allowed")
        elif b_rashi==g_rashi and b_nak!=g_nak: n_final=8; n_reason="Exception: Same Rashi"; logs.append("Nadi: Same Rashi")
        elif friends: n_final=8; n_reason="Cancelled: Strong Maitri"; logs.append("Nadi: Cancelled by Maitri")
    score += n_final; bd.append(("Nadi", n_raw, n_final, 8, n_reason))

    # South Indian
    rajju_group = [0, 1, 2, 3, 4, 3, 2, 1, 0] * 3
    rajju_status = "Fail" if rajju_group[b_nak] == rajju_group[g_nak] else "Pass"
    if rajju_status == "Fail" and (friends or b_rashi == g_rashi): rajju_status = "Cancelled"
    
    vedha_pairs = {0: 17, 1: 16, 2: 15, 3: 14, 4: 22, 5: 21, 6: 20, 7: 19, 8: 18, 9: 26, 10: 25, 11: 24, 12: 23, 13: 13}
    for k, v in list(vedha_pairs.items()): vedha_pairs[v] = k
    vedha_status = "Fail" if vedha_pairs.get(g_nak) == b_nak else "Pass"

    return score, bd, logs, rajju_status, vedha_status

# --- DISCOVERY LOGIC (TAB 2) ---
def find_best_matches(source_gender, s_nak, s_rashi):
    matches = []
    for i in range(27):
        target_star_name = NAKSHATRAS[i]
        valid_rashi_indices = NAK_TO_RASHI_MAP[i]
        for r_idx in valid_rashi_indices:
            target_rashi_name = RASHIS[r_idx]
            if source_gender == "Boy":
                score, _, _, _, _ = calculate_all(s_nak, s_rashi, i, r_idx)
            else:
                score, _, _, _, _ = calculate_all(i, r_idx, s_nak, s_rashi)
            
            matches.append({
                "Star": target_star_name,
                "Rashi": target_rashi_name,
                "Score": score
            })
    return sorted(matches, key=lambda x: x['Score'], reverse=True)

# --- UI START ---
c_title, c_reset = st.columns([4, 1])
with c_title:
    st.title("🕉️ Vedic Matcher")
with c_reset:
    if st.button("🔄 Reset"):
        st.session_state.input_mode = "Birth Details"
        st.session_state.calculated = False
        st.rerun()

# --- 4 DISTINCT TABS (REMOVED DAILY GUIDE) ---
tabs = st.tabs(["❤️ Match", "🔍 Find Matches", "💍 Wedding Dates", "🤖 Guru AI"])

# --- TAB 1: MATCH ---
with tabs[0]:
    input_method = st.radio("Mode:", ["Birth Details", "Direct Star Entry"], horizontal=True, key="input_mode")
    
    if input_method == "Birth Details":
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 🤵 Boy")
            b_date = st.date_input("Date", datetime.date(1995,1,1), key="b_d")
            b_time = st.time_input("Time", datetime.time(10,0), key="b_t")
            b_city = st.text_input("City", "Hyderabad", key="b_c")
        with c2:
            st.markdown("### 👰 Girl")
            g_date = st.date_input("Date", datetime.date(1994,11,28), key="g_d")
            g_time = st.time_input("Time", datetime.time(7,30), key="g_t")
            g_city = st.text_input("City", "Hyderabad", key="g_c")
    else:
        c1, c2 = st.columns(2)
        with c1:
            b_star = st.selectbox("Boy Star", NAKSHATRAS, key="b_s")
            b_rashi_opts = [RASHIS[i] for i in NAK_TO_RASHI_MAP[NAKSHATRAS.index(b_star)]]
            b_rashi_sel = st.selectbox("Boy Rashi", b_rashi_opts, key="b_r")
        with c2:
            g_star = st.selectbox("Girl Star", NAKSHATRAS, index=11, key="g_s")
            g_rashi_opts = [RASHIS[i] for i in NAK_TO_RASHI_MAP[NAKSHATRAS.index(g_star)]]
            try: g_def_idx = g_rashi_opts.index("Virgo (Kanya)")
            except: g_def_idx = 0
            g_rashi_sel = st.selectbox("Girl Rashi", g_rashi_opts, index=g_def_idx, key="g_r")

    if st.button("Check Compatibility", type="primary", use_container_width=True):
        try:
            with st.spinner("Aligning stars..."):
                if input_method == "Birth Details":
                    b_moon, b_mars_l, _, _ = get_planetary_positions(b_date, b_time, b_city, "India")
                    g_moon, g_mars_l, _, _ = get_planetary_positions(g_date, g_time, g_city, "India")
                    b_nak, b_rashi = get_nak_rashi(b_moon)
                    g_nak, g_rashi = get_nak_rashi(g_moon)
                    b_mars = check_mars_dosha_smart(b_rashi, b_mars_l)
                    g_mars = check_mars_dosha_smart(g_rashi, g_mars_l)
                else:
                    b_nak = NAKSHATRAS.index(b_star); b_rashi = RASHIS.index(b_rashi_sel)
                    g_nak = NAKSHATRAS.index(g_star); g_rashi = RASHIS.index(g_rashi_sel)
                    b_mars = (False, "Unknown"); g_mars = (False, "Unknown")

                score, breakdown, logs, rajju, vedha = calculate_all(b_nak, b_rashi, g_nak, g_rashi)
                st.session_state.results = {"score": score, "bd": breakdown, "logs": logs, 
                                            "b_n": NAKSHATRAS[b_nak], "g_n": NAKSHATRAS[g_nak],
                                            "b_prof": NAK_TRAITS.get(b_nak), "g_prof": NAK_TRAITS.get(g_nak),
                                            "b_mars": b_mars, "g_mars": g_mars, "rajju": rajju, "vedha": vedha}
                st.session_state.calculated = True
        except Exception as e: st.error(f"Error: {e}")

    if st.session_state.calculated:
        res = st.session_state.results
        st.markdown("---")
        score_val = res['score']
        score_color = "#ff4b4b" 
        if score_val >= 18: score_color = "#ffa500"
        if score_val >= 25: score_color = "#00cc00"

        col_score, col_gauge = st.columns([1,1])
        with col_score:
            st.markdown(f"<h1 style='text-align: center; color: {score_color}; margin:0;'>{res['score']}</h1>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center;'>out of 36</p>", unsafe_allow_html=True)
            status = "Excellent Match ✅" if res['score'] > 24 else ("Good Match ⚠️" if res['score'] > 18 else "Not Recommended ❌")
            st.markdown(f"<h3 style='text-align: center; color: {score_color};'>{status}</h3>", unsafe_allow_html=True)
        with col_gauge:
            fig = go.Figure(go.Indicator(mode = "gauge", value = res['score'], gauge = {'axis': {'range': [0, 36]}, 'bar': {'color': score_color}}))
            fig.update_layout(height=150, margin=dict(l=10, r=10, t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)

        share_text = f"Match Report: {res['b_n']} w/ {res['g_n']}. Score: {res['score']}/36. {status}"
        st.code(share_text, language="text")
        
        st.markdown("### 📋 Quick Scan")
        for item in res['bd']:
            attr, raw, final, max_pts, reason = item
            border_class = "border-green" if final == max_pts else ("border-orange" if final > 0 else "border-red")
            text_class = "text-green" if final == max_pts else ("text-orange" if final > 0 else "text-red")
            st.markdown(f"""
            <div class="guna-card {border_class}">
                <div class="guna-header">
                    <span>{attr}</span>
                    <span class="guna-score {text_class}">{final} / {max_pts}</span>
                </div>
                <div class="guna-reason">{reason}</div>
            </div>
            """, unsafe_allow_html=True)
            
        with st.expander("📊 Detailed Transparency Table (Raw vs Final)"):
            df = pd.DataFrame(res['bd'], columns=["Attribute", "Raw Score", "Final Score", "Max", "Logic"])
            totals = pd.DataFrame([["TOTAL", df["Raw Score"].sum(), df["Final Score"].sum(), 36, "-"]], columns=df.columns)
            st.table(pd.concat([df, totals], ignore_index=True))
            
        if res['logs']:
            with st.expander("✨ Astrologer's Notes (Dosha Cancellations)"):
                for log in res['logs']: st.info(log)
        
        with st.expander("🪐 Mars & Dosha Analysis"):
            st.write(f"**Rajju:** {res['rajju']} (Body Check)")
            st.write(f"**Vedha:** {res['vedha']} (Enemy Check)")
            st.write(f"**Boy Mars:** {res['b_mars'][1]}")
            st.write(f"**Girl Mars:** {res['g_mars'][1]}")

# --- TAB 2: FIND MATCHES ---
with tabs[1]:
    st.header("🔍 Match Finder")
    st.caption("Find the best compatible stars for you.")
    
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        finder_gender = st.selectbox("I am a", ["Boy", "Girl"])
        finder_star = st.selectbox("My Star", NAKSHATRAS)
    with col_f2:
        finder_rashi_opts = [RASHIS[i] for i in NAK_TO_RASHI_MAP[NAKSHATRAS.index(finder_star)]]
        finder_rashi = st.selectbox("My Rashi", finder_rashi_opts)
    
    if st.button("Find Best Matches", type="primary"):
        with st.spinner("Scanning all 27 stars..."):
            s_nak = NAKSHATRAS.index(finder_star)
            s_rashi = RASHIS.index(finder_rashi)
            matches = find_best_matches(finder_gender, s_nak, s_rashi)
            
            st.success(f"Found {len(matches)} combinations!")
            st.markdown("### Top Matches")
            
            df_matches = pd.DataFrame(matches)
            df_matches['Rating'] = df_matches['Score'].apply(lambda x: "⭐⭐⭐" if x > 25 else ("⭐⭐" if x > 18 else "⭐"))
            st.dataframe(df_matches, use_container_width=True, hide_index=True)

# --- TAB 3: WEDDING DATES ---
with tabs[2]:
    st.header("💍 Wedding Dates")
    t_rashi = st.selectbox("Select Moon Sign (Rashi)", RASHIS, key="t_r")
    if st.button("Check Auspicious Dates"):
        r_idx = RASHIS.index(t_rashi)
        st.subheader("Lucky Years (Jupiter)")
        
        for y, s in predict_marriage_luck_years(r_idx):
            icon = "✅" if "Excellent" in s else "😐"
            st.write(f"**{y}:** {icon} {s}")
        st.subheader("Lucky Month (Sun)")
        
        st.info(f"❤️ **{predict_wedding_month(r_idx)}** (Recurring Annually)")

# --- TAB 4: AI GURU ---
with tabs[3]:
    st.header("🤖 Guru AI")
    user_key = st.text_input("API Key", type="password")
    if user_key and (query := st.chat_input("Ask about today's stars...")):
        genai.configure(api_key=user_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        with st.spinner("Thinking..."):
            st.write(model.generate_content(query).text)
