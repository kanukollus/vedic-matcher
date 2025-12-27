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
import io

# --- PAGE CONFIG (Mobile Friendly) ---
st.set_page_config(page_title="Vedic Matcher Pro", page_icon="🕉️", layout="centered")

# --- SESSION STATE INITIALIZATION ---
if "calculated" not in st.session_state:
    st.session_state.calculated = False
if "results" not in st.session_state:
    st.session_state.results = {}
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- HELPERS & DATA ---
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

NAK_TRAITS = {
    0: {"Symbol": "Horse Head", "Animal": "Horse", "Trait": "Pioneer"}, 1: {"Symbol": "Yoni", "Animal": "Elephant", "Trait": "Creative"}, 2: {"Symbol": "Blade", "Animal": "Sheep", "Trait": "Sharp"},
    3: {"Symbol": "Chariot", "Animal": "Serpent", "Trait": "Sensual"}, 4: {"Symbol": "Deer Head", "Animal": "Serpent", "Trait": "Curious"}, 5: {"Symbol": "Teardrop", "Animal": "Dog", "Trait": "Intellectual"},
    6: {"Symbol": "Quiver", "Animal": "Cat", "Trait": "Nurturing"}, 7: {"Symbol": "Flower", "Animal": "Goat", "Trait": "Spiritual"}, 8: {"Symbol": "Coiled Snake", "Animal": "Cat", "Trait": "Mystical"},
    9: {"Symbol": "Throne", "Animal": "Rat", "Trait": "Royal"}, 10: {"Symbol": "Bed", "Animal": "Rat", "Trait": "Social"}, 11: {"Symbol": "Bed Legs", "Animal": "Cow", "Trait": "Charitable"},
    12: {"Symbol": "Hand", "Animal": "Buffalo", "Trait": "Skilled"}, 13: {"Symbol": "Pearl", "Animal": "Tiger", "Trait": "Beautiful"}, 14: {"Symbol": "Shoot", "Animal": "Buffalo", "Trait": "Independent"},
    15: {"Symbol": "Arch", "Animal": "Tiger", "Trait": "Focused"}, 16: {"Symbol": "Lotus", "Animal": "Deer", "Trait": "Friendship"}, 17: {"Symbol": "Umbrella", "Animal": "Deer", "Trait": "Protective"},
    18: {"Symbol": "Roots", "Animal": "Dog", "Trait": "Deep"}, 19: {"Symbol": "Fan", "Animal": "Monkey", "Trait": "Invincible"}, 20: {"Symbol": "Tusk", "Animal": "Mongoose", "Trait": "Victory"},
    21: {"Symbol": "Ear", "Animal": "Monkey", "Trait": "Listener"}, 22: {"Symbol": "Drum", "Animal": "Lion", "Trait": "Musical"}, 23: {"Symbol": "Circle", "Animal": "Horse", "Trait": "Healer"},
    24: {"Symbol": "Sword", "Animal": "Lion", "Trait": "Passionate"}, 25: {"Symbol": "Twins", "Animal": "Cow", "Trait": "Ascetic"}, 26: {"Symbol": "Drum", "Animal": "Elephant", "Trait": "Complete"}
}

# --- OPTIMIZED CACHING ---
@st.cache_resource
def get_geolocator(): return Nominatim(user_agent="vedic_matcher_v22_human_logic", timeout=10)
@st.cache_resource
def get_tf(): return TimezoneFinder()

@st.cache_data(ttl=3600)
def get_cached_coords(city, country):
    geolocator = get_geolocator()
    try: return geolocator.geocode(f"{city}, {country}")
    except: return None

def get_offset_smart(city, country, dt, manual_tz):
    tf = get_tf()
    loc = get_cached_coords(city, country)
    try:
        if loc:
            tz_name = tf.timezone_at(lng=loc.longitude, lat=loc.latitude)
            if tz_name:
                timezone = pytz.timezone(tz_name)
                localized_dt = timezone.localize(dt)
                return localized_dt.utcoffset().total_seconds() / 3600.0, f"📍 Found: {city}"
        raise ValueError
    except: return manual_tz, f"⚠️ Using Manual TZ: {manual_tz}"

def get_planetary_positions(date_obj, time_obj, city, country, manual_tz):
    dt = datetime.datetime.combine(date_obj, time_obj)
    offset, msg = get_offset_smart(city, country, dt, manual_tz)
    obs = ephem.Observer(); obs.date = dt - datetime.timedelta(hours=offset)
    moon = ephem.Moon(); moon.compute(obs); ecl_moon = ephem.Ecliptic(moon)
    mars = ephem.Mars(); mars.compute(obs); ecl_mars = ephem.Ecliptic(mars)
    ayanamsa = 23.85 + (dt.year - 2000) * 0.01396
    sidereal_moon = (math.degrees(ecl_moon.lon) - ayanamsa) % 360
    sidereal_mars = (math.degrees(ecl_mars.lon) - ayanamsa) % 360
    return sidereal_moon, sidereal_mars, msg

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

# --- ADVANCED CALCULATION LOGIC (HUMANIZED) ---
def calculate_all(b_nak, b_rashi, g_nak, g_rashi):
    # PRELIMINARY DATA
    maitri_raw_score = MAITRI_TABLE[RASHI_LORDS[b_rashi]][RASHI_LORDS[g_rashi]]
    is_friends = maitri_raw_score >= 4
    bhakoot_dist = (b_rashi - g_rashi) % 12
    bhakoot_raw_val = 7 if bhakoot_dist not in [1, 11, 4, 8, 5, 7] else 0
    nadi_raw_val = 0 if NADI_TYPE[b_nak] == NADI_TYPE[g_nak] else 8
    
    score = 0
    breakdown = []
    cancellation_logs = []
    
    # 1. VARNA
    varna_raw = 1 if VARNA_GROUP[b_rashi] <= VARNA_GROUP[g_rashi] else 0
    varna_final = varna_raw
    reason = "Natural Match" if varna_raw == 1 else "Mismatch"
    
    if varna_raw == 0 and is_friends: 
        varna_final = 1; reason = "Boosted by Friendship (Maitri)"
        cancellation_logs.append(f"**Varna:** Score 0 ➝ 1 because of strong **Maitri** (Planetary Friendship).")
    score += varna_final; breakdown.append(("Varna", varna_raw, varna_final, 1, reason))
    
    # 2. VASHYA
    vashya_raw = 0
    if VASHYA_GROUP[b_rashi] == VASHYA_GROUP[g_rashi]: vashya_raw = 2
    elif (VASHYA_GROUP[b_rashi] == 0 and VASHYA_GROUP[g_rashi] == 1) or (VASHYA_GROUP[b_rashi] == 1 and VASHYA_GROUP[g_rashi] == 0): vashya_raw = 1 
    elif VASHYA_GROUP[b_rashi] != VASHYA_GROUP[g_rashi]: vashya_raw = 0.5 
    vashya_final = vashya_raw
    reason = "Match" if vashya_raw >= 1 else "Mismatch"
    
    id_b, id_g = YONI_ID[b_nak], YONI_ID[g_nak]
    yoni_full_match = (id_b == id_g)
    
    if vashya_raw < 2 and (is_friends or yoni_full_match): 
        vashya_final = 2; reason = "Boosted by Maitri/Yoni"
        why = "Friendship (Maitri)" if is_friends else "Perfect Yoni"
        cancellation_logs.append(f"**Vashya:** Score {vashya_raw} ➝ 2 due to **{why}**.")
    score += vashya_final; breakdown.append(("Vashya", vashya_raw, vashya_final, 2, reason))
    
    # 3. TARA
    count = (b_nak - g_nak) % 27 + 1
    tara_raw = 3 if count % 9 not in [3, 5, 7] else 0
    tara_final = tara_raw
    reason = "Benefic" if tara_raw == 3 else "Malefic"
    
    if tara_raw == 0 and is_friends: 
        tara_final = 3; reason = "Boosted by Friendship (Maitri)"
        cancellation_logs.append(f"**Tara:** Score 0 ➝ 3 due to **Maitri** (Planetary Friendship).")
    score += tara_final; breakdown.append(("Tara", tara_raw, tara_final, 3, reason))
    
    # 4. YONI
    yoni_raw = 4 if id_b == id_g else (0 if YONI_Enemy_Map.get(id_b) == id_g or YONI_Enemy_Map.get(id_g) == id_b else 2)
    yoni_final = yoni_raw
    reason = "Same Species" if yoni_raw == 4 else ("Enemy Species" if yoni_raw == 0 else "Neutral")
    
    if yoni_raw < 4:
        if is_friends or bhakoot_raw_val == 7 or vashya_final >= 1: 
            yoni_final = 4; reason = "Compensated by Maitri/Bhakoot"
            why = "Maitri (Friendship)" if is_friends else ("Bhakoot (Love)" if bhakoot_raw_val==7 else "Vashya (Attraction)")
            cancellation_logs.append(f"**Yoni:** Score {yoni_raw} ➝ 4. Physical mismatch ignored due to strong **{why}**.")
    score += yoni_final; breakdown.append(("Yoni", yoni_raw, yoni_final, 4, reason))
    
    # 5. MAITRI
    maitri_final = maitri_raw_score
    reason = "Friendly" if maitri_raw_score >= 4 else "Enemy"
    
    if maitri_raw_score < 4 and bhakoot_raw_val == 7: 
        maitri_final = 5; reason = "Compensated by Bhakoot (Love)"
        cancellation_logs.append(f"**Maitri:** Score {maitri_raw_score} ➝ 5. Friendship boosted by strong **Bhakoot** (Emotional Bond).")
    score += maitri_final; breakdown.append(("Maitri", maitri_raw_score, maitri_final, 5, reason))
    
    # 6. GANA
    gb, gg = GANA_TYPE[b_nak], GANA_TYPE[g_nak]
    gana_raw = 6 if gb == gg else (0 if (gg==1 and gb==2) or (gg==2 and gb==1) else (1 if (gg==0 and gb==2) or (gg==2 and gb==0) else 5))
    gana_final = gana_raw
    reason = "Match" if gana_raw >= 5 else "Mismatch"
    
    star_dist_gb = (g_nak - b_nak) % 27
    if gana_raw < 6:
        if is_friends or bhakoot_raw_val == 7 or star_dist_gb > 14: 
            gana_final = 6; reason = "Compensated by Maitri/Bhakoot"
            why = "Maitri (Friendship)" if is_friends else ("Bhakoot (Love)" if bhakoot_raw_val==7 else "Distance")
            cancellation_logs.append(f"**Gana:** Score {gana_raw} ➝ 6. Temperament difference ignored due to **{why}**.")
    score += gana_final; breakdown.append(("Gana", gana_raw, gana_final, 6, reason))
    
    # 7. BHAKOOT
    bhakoot_final = bhakoot_raw_val
    reason = "Good" if bhakoot_raw_val == 7 else "Dosha"
    
    if bhakoot_raw_val == 0:
        if is_friends or nadi_raw_val == 8: 
            bhakoot_final = 7; reason = "Compensated by Maitri/Nadi"
            why = "Maitri (Friendship)" if is_friends else "Nadi (Health)"
            cancellation_logs.append(f"**Bhakoot:** Score 0 ➝ 7. Emotional mismatch ignored due to strong **{why}**.")
    score += bhakoot_final; breakdown.append(("Bhakoot", bhakoot_raw_val, bhakoot_final, 7, reason))
    
    # 8. NADI
    nadi_final = nadi_raw_val
    nadi_msg = "OK" if nadi_raw_val == 8 else "Dosha"
    nadi_reason = "Healthy" if nadi_raw_val == 8 else "Same Nadi"
    
    if nadi_raw_val == 0:
        if b_nak == g_nak and NAKSHATRAS[b_nak] in SAME_NAKSHATRA_ALLOWED:
             nadi_final = 8; nadi_reason = "Exception: Allowed Star"; nadi_msg = "Exception: Allowed Star"
             cancellation_logs.append(f"**Nadi:** Score 0 ➝ 8 because **{NAKSHATRAS[b_nak]}** is a special allowed star.")
        elif b_rashi == g_rashi and b_nak != g_nak:
             nadi_final = 8; nadi_reason = "Cancelled: Same Rashi"; nadi_msg = "Cancelled (Same Rashi)"
             cancellation_logs.append(f"**Nadi:** Score 0 ➝ 8 because Rashi is same but Stars are different.")
        elif is_friends:
             nadi_final = 8; nadi_reason = "Compensated by Maitri"; nadi_msg = "Cancelled (Friendship)"
             cancellation_logs.append(f"**Nadi:** Score 0 ➝ 8 due to Strong **Maitri** (Friendship).")
             
    score += nadi_final; breakdown.append(("Nadi", nadi_raw_val, nadi_final, 8, nadi_reason))
    
    # SOUTH INDIAN CHECKS
    rajju_group = [0, 1, 2, 3, 4, 3, 2, 1, 0] * 3
    rajju_status = "Fail" if rajju_group[b_nak] == rajju_group[g_nak] else "Pass"
    if rajju_status == "Fail" and (is_friends or b_rashi == g_rashi): 
        rajju_status = "Cancelled"
        cancellation_logs.append("**Rajju Dosha:** Cancelled due to strong Maitri/Rashi Match.")
    
    vedha_pairs = {0: 17, 1: 16, 2: 15, 3: 14, 4: 22, 5: 21, 6: 20, 7: 19, 8: 18, 9: 26, 10: 25, 11: 24, 12: 23, 13: 13}
    for k, v in list(vedha_pairs.items()): vedha_pairs[v] = k
    vedha_status = "Fail" if vedha_pairs.get(g_nak) == b_nak else "Pass"
    
    return score, breakdown, rajju_status, vedha_status, nadi_msg, cancellation_logs

def calculate_advanced(b_nak, g_nak):
    count = (b_nak - g_nak) % 27 + 1
    mahendra = "Present ✅" if count in [4, 7, 10, 13, 16, 19, 22, 25] else "Standard (Neutral)"
    dist = (b_nak - g_nak) % 27
    stree = "Excellent ✅" if dist > 13 else ("Good" if dist > 7 else "Average (Neutral)")
    dina = "Good ✅" if (count % 9) in [2, 4, 6, 8, 0] else "Average (Neutral)"
    return mahendra, stree, dina

def create_gauge(score):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number", value = score,
        gauge = {'axis': {'range': [None, 36]}, 'bar': {'color': "rgba(0,0,0,0)"},
                 'steps': [{'range': [0, 18], 'color': "#ffcccb"}, {'range': [18, 25], 'color': "#ffffcc"}, {'range': [25, 36], 'color': "#90ee90"}],
                 'threshold': {'line': {'color': "black", 'width': 4}, 'thickness': 0.75, 'value': score}}))
    fig.update_layout(height=250, margin=dict(l=10, r=10, t=40, b=10))
    return fig

def handle_ai_query(prompt, context_str, key):
    try:
        genai.configure(api_key=key)
        # Auto-detect logic
        model_name = "gemini-1.5-flash"
        try:
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    if 'flash' in m.name: model_name = m.name; break
                    elif 'pro' in m.name: model_name = m.name
        except: pass
        model = genai.GenerativeModel(model_name)
        chat = model.start_chat(history=[{"role": "user", "parts": [context_str]}, {"role": "model", "parts": ["I understand."]}])
        response = chat.send_message(prompt)
        return response.text
    except Exception as e: return f"Error: {e}"

def create_report_text(b_n, g_n, sc, r, v, b_p, g_p, bd):
    txt = f"MATCH REPORT\nBoy: {b_n} ({b_p['Trait']})\nGirl: {g_n} ({g_p['Trait']})\nScore: {sc}/36\nRajju: {r}\nVedha: {v}\n\nDETAILED SCORES:\n"
    for item in bd: txt += f"{item[0]}: Raw {item[1]} -> Final {item[2]} / {item[3]} ({item[4]})\n"
    return txt

# --- MAIN LAYOUT (MOBILE FIRST) ---
c_title, c_reset = st.columns([3, 1])
with c_title:
    st.title("🕉️ Vedic Matcher")
    st.caption("Powered by Google Gemini ♊")
with c_reset:
    if st.button("🔄 Reset", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# TABS NAVIGATION
tab_match, tab_time, tab_ai = st.tabs(["❤️ Match", "📅 Timing", "🤖 AI Guru"])

# --- TAB 1: MATCH ---
with tab_match:
    st.caption("Calculate compatibility score & Doshas.")
    input_method = st.radio("Mode:", ["Birth Details", "Direct Star Entry"], horizontal=True)
    
    if input_method == "Birth Details":
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Boy")
            b_date = st.date_input("Date", datetime.date(1995, 1, 1), key="b_d")
            b_time = st.time_input("Time", datetime.time(10, 0), step=60, key="b_t")
            b_city = st.text_input("City", "Hyderabad", key="b_c")
            b_country = st.text_input("Country", "India", key="b_co")
        with c2:
            st.subheader("Girl")
            g_date = st.date_input("Date", datetime.date(1994, 11, 28), key="g_d")
            g_time = st.time_input("Time", datetime.time(7, 30), step=60, key="g_t")
            g_city = st.text_input("City", "Hyderabad", key="g_c")
            g_country = st.text_input("Country", "India", key="g_co")
    else:
        c1, c2 = st.columns(2)
        with c1:
            b_star = st.selectbox("Boy Star", NAKSHATRAS, index=0, key="b_s") # Ashwini
            b_rashi_opts = [RASHIS[i] for i in NAK_TO_RASHI_MAP[NAKSHATRAS.index(b_star)]]
            b_rashi_sel = st.selectbox("Boy Rashi", b_rashi_opts, key="b_r")
        with c2:
            g_star = st.selectbox("Girl Star", NAKSHATRAS, index=11, key="g_s") # Uttara Phalguni
            # Smart Default: If Virgo (Kanya) is in list, select it. Else 0.
            g_rashi_opts = [RASHIS[i] for i in NAK_TO_RASHI_MAP[NAKSHATRAS.index(g_star)]]
            try: g_def_idx = g_rashi_opts.index("Virgo (Kanya)")
            except: g_def_idx = 0
            g_rashi_sel = st.selectbox("Girl Rashi", g_rashi_opts, index=g_def_idx, key="g_r")

    if st.button("Calculate Match", type="primary", use_container_width=True):
        try:
            if input_method == "Birth Details":
                with st.spinner("Analyzing stars..."):
                    b_moon, b_mars_l, b_msg = get_planetary_positions(b_date, b_time, b_city, b_country, 5.5)
                    g_moon, g_mars_l, g_msg = get_planetary_positions(g_date, g_time, g_city, g_country, 5.5)
                    if b_moon is None: st.error("Location Error"); st.stop()
                    
                    b_nak, b_rashi = get_nak_rashi(b_moon)
                    g_nak, g_rashi = get_nak_rashi(g_moon)
                    
                    b_mars = check_mars_dosha_smart(b_rashi, b_mars_l)
                    g_mars = check_mars_dosha_smart(g_rashi, g_mars_l)
                    
                    st.success("✅ Calculations Complete!")
                    val1, val2 = st.columns(2)
                    val1.info(f"**Boy:** {NAKSHATRAS[b_nak]} ({RASHIS[b_rashi]})")
                    val2.info(f"**Girl:** {NAKSHATRAS[g_nak]} ({RASHIS[g_rashi]})")
                    
            else:
                b_nak = NAKSHATRAS.index(b_star); b_rashi = RASHIS.index(b_rashi_sel)
                g_nak = NAKSHATRAS.index(g_star); g_rashi = RASHIS.index(g_rashi_sel)
                b_mars = (False, "Unknown"); g_mars = (False, "Unknown")

            score, breakdown, rajju, vedha, nadi_msg, logs = calculate_all(b_nak, b_rashi, g_nak, g_rashi)
            mahendra, stree, dina = calculate_advanced(b_nak, g_nak)
            
            st.session_state.results = {
                "score": score, "b_nak": NAKSHATRAS[b_nak], "g_nak": NAKSHATRAS[g_nak],
                "b_rashi": RASHIS[b_rashi], "g_rashi": RASHIS[g_rashi], "rajju": rajju,
                "vedha": vedha, "breakdown": breakdown, "nadi_msg": nadi_msg, "logs": logs,
                "b_mars": b_mars, "g_mars": g_mars, "mahendra": mahendra, "stree": stree, "dina": dina,
                "b_prof": NAK_TRAITS.get(b_nak), "g_prof": NAK_TRAITS.get(g_nak),
                "b_rashi_idx": b_rashi, "g_rashi_idx": g_rashi
            }
            st.session_state.calculated = True
        except Exception as e: st.error(f"Error: {e}")

    # RESULTS UI
    if st.session_state.calculated:
        res = st.session_state.results
        st.divider()
        c_res1, c_res2 = st.columns([2, 1])
        with c_res1:
            st.subheader(f"Score: {res['score']} / 36")
            if res['score'] >= 18 and res['rajju'] != "Fail": st.success("✅ Good Match")
            else: st.warning("⚠️ Review Needed")
        with c_res2:
            st.plotly_chart(create_gauge(res['score']), use_container_width=True)
        
        # TRANSPARENCY REPORT (ONLY IF LOGS EXIST)
        if res.get('logs'):
            with st.container():
                st.info("ℹ️ Some Doshas were **cancelled** based on special rules (see Logic Logs below).")
        
        with st.expander("📊 Detailed Table & Logic", expanded=True):
            # Prep Table
            df_display = pd.DataFrame(res['breakdown'], columns=["Attribute", "Raw Score", "Final Score", "Max", "Reasoning"])
            
            # Add TOTAL Row
            raw_sum = df_display["Raw Score"].sum()
            final_sum = df_display["Final Score"].sum()
            max_sum = df_display["Max"].sum()
            
            # Using concat instead of append (pandas 2.0 friendly)
            new_row = pd.DataFrame([["TOTAL", raw_sum, final_sum, max_sum, "-"]], columns=df_display.columns)
            df_display = pd.concat([df_display, new_row], ignore_index=True)
            
            st.table(df_display)
            
            if res.get('logs'):
                st.markdown("#### 🔍 Logic Logs")
                for log in res['logs']: st.caption(f"• {log}")
            
            # Downloads
            txt_data = create_report_text(res['b_nak'], res['g_nak'], res['score'], res['rajju'], res['vedha'], res['b_prof'], res['g_prof'], res['breakdown'])
            st.download_button("📥 Save Detailed Report (TXT)", txt_data, "report.txt")
            
        with st.expander("🪐 Dosha Analysis (Mars/Rajju)"):
            st.write(f"**Rajju:** {res['rajju']} (Body Check)")
            st.write(f"**Vedha:** {res['vedha']} (Enemy Check)")
            st.write(f"**Boy Mars:** {res['b_mars'][1]}")
            st.write(f"**Girl Mars:** {res['g_mars'][1]}")

# --- TAB 2: TIMING ---
with tab_time:
    st.header("📅 Wedding Timing")
    st.caption("Best time based on Boy/Girl Moon Sign.")
    
    t_rashi = st.selectbox("Select Moon Sign (Rashi)", RASHIS, key="t_r")
    if st.button("Check Auspicious Dates", use_container_width=True):
        r_idx = RASHIS.index(t_rashi)
        st.divider()
        st.subheader("Lucky Years (Jupiter)")
        
        for y, s in predict_marriage_luck_years(r_idx):
            icon = "✅" if "Excellent" in s else "😐"
            st.write(f"**{y}:** {icon} {s}")
        
        st.divider()
        st.subheader("Lucky Month (Sun)")
        
        st.info(f"💍 **{predict_wedding_month(r_idx)}** (Recurring Annually)")

# --- TAB 3: AI GURU ---
with tab_ai:
    st.header("🤖 Ask the Guru")
    
    # MOBILE FRIENDLY KEY INPUT
    user_key = None
    if "GEMINI_API_KEY" in st.secrets:
        user_key = st.secrets["GEMINI_API_KEY"]
    else:
        user_key = st.text_input("🔑 Enter Gemini API Key", type="password", placeholder="Paste key here if not in sidebar")
    
    if not user_key:
        st.warning("API Key needed. Get one free at aistudio.google.com")
    else:
        # Context
        context = "You are a Vedic Astrologer."
        suggestions = ["Best wedding colors?", "Remedies for Nadi Dosha?", "Explain Rajju Dosha"]
        
        if st.session_state.calculated:
            r = st.session_state.results
            context += f" Match Context: Boy {r['b_nak']}, Girl {r['g_nak']}. Score: {r['score']}. Doshas: Rajju={r['rajju']}, Vedha={r['vedha']}."
            suggestions = ["Analyze this match score", "Remedies for this couple?", "Is Mars Dosha an issue here?"]
            st.success(f"Context Loaded: {r['b_nak']} ❤️ {r['g_nak']}")
        
        # Suggestion Buttons
        cols = st.columns(3)
        clicked_prompt = None
        for i, s in enumerate(suggestions):
            if cols[i].button(s, use_container_width=True): clicked_prompt = s
            
        # Chat
        for m in st.session_state.messages:
            with st.chat_message(m["role"]): st.write(m["content"])
            
        if (prompt := st.chat_input("Ask a question...")) or clicked_prompt:
            final_prompt = prompt if prompt else clicked_prompt
            st.session_state.messages.append({"role": "user", "content": final_prompt})
            with st.chat_message("user"): st.write(final_prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("Consulting texts..."):
                    ans = handle_ai_query(final_prompt, context, user_key)
                    st.write(ans)
                    st.session_state.messages.append({"role": "assistant", "content": ans})

# --- FOOTER ---
st.divider()
with st.expander("ℹ️ How to Read Results & Disclaimer"):
    st.markdown("""
    ### **1. The Score (Gunas)**
    * **18-24:** Good Match.
    * **25-36:** Excellent Match.
    * **Below 18:** Not recommended without remedies.

    ### **2. The Critical Checks (Doshas)**
    * **Rajju (Body):** Must be 'Pass'. Indicates physical safety.
    * **Vedha (Enemy):** Must be 'Pass'. Indicates conflict.
    * **Nadi (Genes):** Critical for health/lineage.

    ### **3. Mars (Mangal) Dosha**
    * Checks if Mars energy is balanced between the couple.
    * *Note: This app automatically checks for cancellations (e.g., Mars in own house).*
    """)
    st.caption("----------------------------------------------------------------")
    st.caption("⚠️ **Disclaimer:** This tool combines North Indian Ashta Koota and South Indian Das Porutham logic. AI features are powered by Google Gemini. Calculations are based on Lahiri Ayanamsa. This is for informational purposes only; please consult a human astrologer for final marriage decisions.")
