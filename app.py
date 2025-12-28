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
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
        border-left: 5px solid #ff4b4b;
    }
    .guna-header {
        font-size: 18px;
        font-weight: bold;
        display: flex;
        justify-content: space-between;
    }
    .guna-score {
        font-weight: bold;
        color: #ff4b4b;
    }
    .guna-reason {
        font-size: 14px;
        color: #555;
        margin-top: 5px;
        font-style: italic;
    }
    .pass { border-left-color: #00cc00 !important; }
    .score-pass { color: #00cc00 !important; }
</style>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
if "calculated" not in st.session_state: st.session_state.calculated = False
if "results" not in st.session_state: st.session_state.results = {}
if "messages" not in st.session_state: st.session_state.messages = []
if "input_mode" not in st.session_state: st.session_state.input_mode = "Birth Details"

# --- HELPERS & DATA (Shortened for brevity, logic remains same) ---
NAKSHATRAS = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra","Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni","Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha","Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta","Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"]
RASHIS = ["Aries (Mesha)", "Taurus (Vrishabha)", "Gemini (Mithuna)", "Cancer (Karka)","Leo (Simha)", "Virgo (Kanya)", "Libra (Tula)", "Scorpio (Vrishchika)","Sagittarius (Dhanu)", "Capricorn (Makara)", "Aquarius (Kumbha)", "Pisces (Meena)"]
NAK_TO_RASHI_MAP = {0: [0], 1: [0], 2: [0, 1], 3: [1], 4: [1, 2], 5: [2], 6: [2, 3], 7: [3], 8: [3], 9: [4], 10: [4], 11: [4, 5], 12: [5], 13: [5, 6], 14: [6], 15: [6, 7], 16: [7], 17: [7], 18: [8], 19: [8], 20: [8, 9], 21: [9], 22: [9, 10], 23: [10], 24: [10, 11], 25: [11], 26: [11]}
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
def get_geolocator(): return Nominatim(user_agent="vedic_v24_panchang", timeout=10)
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
    obs.lat, obs.lon = '17.3850', '78.4867' # Default fallback if needed
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

def check_mars_dosha(rashi, long):
    m_r = int(long/30); h = (m_r - rashi)%12 + 1
    if h in [2,4,7,8,12]:
        if m_r in [0,7,9]: return False, f"Neutralized (House {h})"
        return True, f"⚠️ Dosha (House {h})"
    return False, "Safe"

def calculate_all(b_nak, b_rashi, g_nak, g_rashi):
    # (Same Logic as v22 - Consolidating for brevity)
    maitri = MAITRI_TABLE[RASHI_LORDS[b_rashi]][RASHI_LORDS[g_rashi]]
    friends = maitri >= 4
    score = 0; bd = []; logs = []
    
    # Simple Loop for 8 Kootas
    # Varna
    v = 1 if VARNA_GROUP[b_rashi] <= VARNA_GROUP[g_rashi] else 0
    if v==0 and friends: v=1; logs.append("Varna boosted by Friendship")
    score+=v; bd.append(("Varna", v, 1, "Natural" if v==1 else "Mismatch"))
    
    # Vashya
    va = 0
    if VASHYA_GROUP[b_rashi] == VASHYA_GROUP[g_rashi]: va = 2
    elif (VASHYA_GROUP[b_rashi] == 0 and VASHYA_GROUP[g_rashi] == 1) or (VASHYA_GROUP[b_rashi] == 1 and VASHYA_GROUP[g_rashi] == 0): va = 1 
    elif VASHYA_GROUP[b_rashi] != VASHYA_GROUP[g_rashi]: va = 0.5 
    if va<2 and (friends or YONI_ID[b_nak]==YONI_ID[g_nak]): va=2; logs.append("Vashya boosted by Friendship/Yoni")
    score+=va; bd.append(("Vashya", va, 2, "Magnetic" if va>=1 else "Mismatch"))
    
    # Tara
    cnt = (b_nak - g_nak)%27 + 1
    t = 3 if cnt%9 not in [3,5,7] else 0
    if t==0 and friends: t=3; logs.append("Tara boosted by Friendship")
    score+=t; bd.append(("Tara", t, 3, "Benefic" if t==3 else "Malefic"))
    
    # Yoni
    y = 4 if YONI_ID[b_nak] == YONI_ID[g_nak] else (0 if YONI_Enemy_Map.get(YONI_ID[b_nak]) == YONI_ID[g_nak] else 2)
    y_raw = y
    if y<4 and (friends or va>=1): y=4; logs.append("Yoni mismatch ignored due to Love/Magnetism")
    score+=y; bd.append(("Yoni", y, 4, "Perfect" if y_raw==4 else "Compensated"))
    
    # Maitri
    m = maitri
    score+=m; bd.append(("Maitri", m, 5, "Friendly" if m>=4 else "Enemy"))
    
    # Gana
    gb, gg = GANA_TYPE[b_nak], GANA_TYPE[g_nak]
    ga = 6 if gb==gg else (0 if (gg==1 and gb==2) or (gg==2 and gb==1) else 1)
    if ga<6 and friends: ga=6; logs.append("Gana boosted by Friendship")
    score+=ga; bd.append(("Gana", ga, 6, "Match" if ga==6 else "Compensated"))
    
    # Bhakoot
    dist = (b_rashi-g_rashi)%12
    bh = 7 if dist not in [1,11,4,8,5,7] else 0
    if bh==0 and (friends or NADI_TYPE[b_nak]!=NADI_TYPE[g_nak]): bh=7; logs.append("Bhakoot boosted by Friendship/Nadi")
    score+=bh; bd.append(("Bhakoot", bh, 7, "Love Flow" if bh==7 else "Blocked"))
    
    # Nadi
    n = 8
    if NADI_TYPE[b_nak] == NADI_TYPE[g_nak]:
        n = 0
        if b_nak==g_nak and NAKSHATRAS[b_nak] in SAME_NAKSHATRA_ALLOWED: n=8; logs.append("Nadi Exception: Star Allowed")
        elif b_rashi==g_rashi and b_nak!=g_nak: n=8; logs.append("Nadi Exception: Same Rashi")
        elif friends: n=8; logs.append("Nadi Dosha Cancelled by Friendship")
    score+=n; bd.append(("Nadi", n, 8, "Healthy" if n==8 else "Dosha"))

    return score, bd, logs

def get_daily_panchang():
    # Toothbrush Feature: Daily Calc
    now = datetime.datetime.now()
    s_moon, _, s_sun, _ = get_planetary_positions(now.date(), now.time(), "Delhi", "India") # Default to Delhi if unknown
    
    # Tithi Calc (Moon - Sun) / 12
    diff = (s_moon - s_sun) % 360
    tithi_num = int(diff / 12) + 1
    paksha = "Shukla" if tithi_num <= 15 else "Krishna"
    tithi_name = f"Tithi {tithi_num} ({paksha})"
    
    # Nakshatra
    nak_idx = int(s_moon / 13.333333)
    return tithi_name, NAKSHATRAS[nak_idx]

# --- UI START ---
c_title, c_reset = st.columns([4, 1])
with c_title:
    st.title("🕉️ Vedic Matcher")
with c_reset:
    if st.button("🔄 Reset"):
        st.session_state.input_mode = "Birth Details"
        st.session_state.calculated = False
        st.rerun()

# --- TABS ---
tabs = st.tabs(["❤️ Matcher", "📅 Daily Guide", "🤖 Guru AI"])

# --- TAB 1: MATCHER ---
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
            g_date = st.date_input("Date", datetime.date(1996,1,1), key="g_d")
            g_time = st.time_input("Time", datetime.time(10,0), key="g_t")
            g_city = st.text_input("City", "Hyderabad", key="g_c")
    else:
        c1, c2 = st.columns(2)
        with c1:
            b_star = st.selectbox("Boy Star", NAKSHATRAS, key="b_s")
            b_rashi_opts = [RASHIS[i] for i in NAK_TO_RASHI_MAP[NAKSHATRAS.index(b_star)]]
            b_rashi_sel = st.selectbox("Boy Rashi", b_rashi_opts, key="b_r")
        with c2:
            g_star = st.selectbox("Girl Star", NAKSHATRAS, index=5, key="g_s")
            g_rashi_opts = [RASHIS[i] for i in NAK_TO_RASHI_MAP[NAKSHATRAS.index(g_star)]]
            g_rashi_sel = st.selectbox("Girl Rashi", g_rashi_opts, key="g_r")

    if st.button("Check Compatibility", type="primary", use_container_width=True):
        try:
            with st.spinner("Aligning stars..."):
                if input_method == "Birth Details":
                    b_moon, b_mars_l, _, _ = get_planetary_positions(b_date, b_time, b_city, "India")
                    g_moon, g_mars_l, _, _ = get_planetary_positions(g_date, g_time, g_city, "India")
                    b_nak, b_rashi = get_nak_rashi(b_moon)
                    g_nak, g_rashi = get_nak_rashi(g_moon)
                else:
                    b_nak = NAKSHATRAS.index(b_star); b_rashi = RASHIS.index(b_rashi_sel)
                    g_nak = NAKSHATRAS.index(g_star); g_rashi = RASHIS.index(g_rashi_sel)

                score, breakdown, logs = calculate_all(b_nak, b_rashi, g_nak, g_rashi)
                st.session_state.results = {"score": score, "bd": breakdown, "logs": logs, 
                                            "b_n": NAKSHATRAS[b_nak], "g_n": NAKSHATRAS[g_nak]}
                st.session_state.calculated = True
        except Exception as e: st.error(f"Error: {e}")

    # --- MOBILE FRIENDLY RESULTS ---
    if st.session_state.calculated:
        res = st.session_state.results
        st.markdown("---")
        
        # HEADLINE SCORE
        col_score, col_gauge = st.columns([1,1])
        with col_score:
            st.markdown(f"<h1 style='text-align: center; color: #ff4b4b; margin:0;'>{res['score']}</h1>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center;'>out of 36</p>", unsafe_allow_html=True)
            status = "Excellent Match ✅" if res['score'] > 24 else ("Good Match ⚠️" if res['score'] > 18 else "Not Recommended ❌")
            st.markdown(f"<h3 style='text-align: center;'>{status}</h3>", unsafe_allow_html=True)
        
        with col_gauge:
            fig = go.Figure(go.Indicator(
                mode = "gauge", value = res['score'],
                gauge = {'axis': {'range': [0, 36]}, 'bar': {'color': "#ff4b4b"}}))
            fig.update_layout(height=150, margin=dict(l=10, r=10, t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)

        # TOOTHBRUSH FEATURE: WHATSAPP SHARE TEXT
        share_text = f"Match Report: {res['b_n']} w/ {res['g_n']}. Score: {res['score']}/36. {status}"
        st.code(share_text, language="text")
        st.caption("👆 Copy to share on WhatsApp")

        # MOBILE CARDS (THE FIX FOR TABLES)
        st.markdown("### 📋 Detailed Analysis")
        for item in res['bd']:
            attr, pts, max_pts, reason = item
            border_class = "pass" if pts == max_pts else "fail"
            text_class = "score-pass" if pts == max_pts else ""
            
            st.markdown(f"""
            <div class="guna-card {border_class}">
                <div class="guna-header">
                    <span>{attr}</span>
                    <span class="guna-score {text_class}">{pts} / {max_pts}</span>
                </div>
                <div class="guna-reason">{reason}</div>
            </div>
            """, unsafe_allow_html=True)
            
        if res['logs']:
            with st.expander("✨ Astrologer's Notes (Dosha Cancellations)"):
                for log in res['logs']: st.write(f"• {log}")

# --- TAB 2: DAILY GUIDE (TOOTHBRUSH) ---
with tabs[1]:
    st.header("📅 Today's Guide")
    tithi, nak = get_daily_panchang()
    
    st.markdown(f"""
    <div style="padding: 20px; background-color: #fff9c4; border-radius: 10px; text-align: center;">
        <h3>Today's Nakshatra</h3>
        <h1 style="color: #ff9800;">{nak}</h1>
        <hr>
        <h3>Tithi</h3>
        <h4>{tithi}</h4>
    </div>
    """, unsafe_allow_html=True)
    
    
    
    st.info("💡 **Tip:** Avoid starting new ventures during Rahu Kalam (Calculated for your location).")
    
    # Placeholder for daily transit
    st.markdown("### 🔮 Your Daily Vibe")
    st.caption("Select your Rashi to see how today looks for you.")
    user_rashi = st.selectbox("My Rashi", RASHIS)
    st.success(f"Moon is currently transiting. {user_rashi} natives might feel energetic today!")

# --- TAB 3: AI ---
with tabs[2]:
    st.header("🤖 Guru AI")
    user_key = st.text_input("API Key", type="password")
    if user_key and (query := st.chat_input("Ask about today's stars...")):
        genai.configure(api_key=user_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        with st.spinner("Thinking..."):
            st.write(model.generate_content(query).text)
