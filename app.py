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

# --- PAGE CONFIG ---
st.set_page_config(page_title="Vedic Matcher Pro", page_icon="🕉️", layout="centered")

# --- SESSION STATE INITIALIZATION ---
if "calculated" not in st.session_state:
    st.session_state.calculated = False
if "results" not in st.session_state:
    st.session_state.results = {}
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- SIDEBAR (API KEY) ---
with st.sidebar:
    st.header("🤖 AI Settings")
    api_key = st.text_input("Google Gemini API Key", type="password", help="Get free key at aistudio.google.com")
    if not api_key:
        st.warning("⚠️ Enter Gemini Key to enable the AI Guru.")
    else:
        st.success("✅ Gemini AI Enabled")
        try:
            genai.configure(api_key=api_key)
        except Exception as e:
            st.error(f"API Error: {e}")

# --- DATA CONSTANTS ---
NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta",
    "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
]

NAK_TRAITS = {
    0: {"Symbol": "Horse Head", "Animal": "Horse", "Trait": "Pioneer, Fast, Independent"},
    1: {"Symbol": "Yoni", "Animal": "Elephant", "Trait": "Creative, Truthful, Struggle"},
    2: {"Symbol": "Blade", "Animal": "Sheep", "Trait": "Sharp, Fire, Purifier"},
    3: {"Symbol": "Chariot", "Animal": "Serpent", "Trait": "Sensual, Nature-lover, Charismatic"},
    4: {"Symbol": "Deer Head", "Animal": "Serpent", "Trait": "Curious, Gentle, Wanderer"},
    5: {"Symbol": "Teardrop", "Animal": "Dog", "Trait": "Emotional, Stormy, Intellectual"},
    6: {"Symbol": "Quiver", "Animal": "Cat", "Trait": "Nurturing, Safe, Returning"},
    7: {"Symbol": "Flower", "Animal": "Goat", "Trait": "Spiritual, Caring, Teacher"},
    8: {"Symbol": "Coiled Snake", "Animal": "Cat", "Trait": "Mystical, Intense, Clinging"},
    9: {"Symbol": "Throne", "Animal": "Rat", "Trait": "Royal, Leader, Ancestral"},
    10: {"Symbol": "Bed (Front)", "Animal": "Rat", "Trait": "Relaxed, Social, Creative"},
    11: {"Symbol": "Bed (Back)", "Animal": "Cow", "Trait": "Helper, Friend, Patron"},
    12: {"Symbol": "Hand", "Animal": "Buffalo", "Trait": "Skilled, Healer, Dexterous"},
    13: {"Symbol": "Pearl", "Animal": "Tiger", "Trait": "Beautiful, Architect, Illusion"},
    14: {"Symbol": "Shoot", "Animal": "Buffalo", "Trait": "Independent, Flexible, Traveler"},
    15: {"Symbol": "Arch", "Animal": "Tiger", "Trait": "Goal-oriented, Focused, Competitive"},
    16: {"Symbol": "Lotus", "Animal": "Deer", "Trait": "Friendship, Devotion, Soft"},
    17: {"Symbol": "Umbrella", "Animal": "Deer", "Trait": "Protective, Senior, Wise"},
    18: {"Symbol": "Roots", "Animal": "Dog", "Trait": "Investigator, Deep, Destructive"},
    19: {"Symbol": "Fan", "Animal": "Monkey", "Trait": "Invincible, Proud, Water"},
    20: {"Symbol": "Tusk", "Animal": "Mongoose", "Trait": "Universal, Victory, Leader"},
    21: {"Symbol": "Ear", "Animal": "Monkey", "Trait": "Listener, Learner, Knowledge"},
    22: {"Symbol": "Drum", "Animal": "Lion", "Trait": "Musical, Wealthy, Famous"},
    23: {"Symbol": "Empty Circle", "Animal": "Horse", "Trait": "Healer, Philosophical, Mystery"},
    24: {"Symbol": "Sword", "Animal": "Lion", "Trait": "Dual-faced, Passionate, Intense"},
    25: {"Symbol": "Twins", "Animal": "Cow", "Trait": "Deep, Watery, Ascetic"},
    26: {"Symbol": "Drum", "Animal": "Elephant", "Trait": "Wealthy, Nourisher, Complete"}
}

SAME_NAKSHATRA_ALLOWED = [
    "Rohini", "Ardra", "Pushya", "Magha", "Vishakha", "Shravana", 
    "Uttara Bhadrapada", "Revati"
]

RASHIS = [
    "Aries (Mesha)", "Taurus (Vrishabha)", "Gemini (Mithuna)", "Cancer (Karka)",
    "Leo (Simha)", "Virgo (Kanya)", "Libra (Tula)", "Scorpio (Vrishchika)",
    "Sagittarius (Dhanu)", "Capricorn (Makara)", "Aquarius (Kumbha)", "Pisces (Meena)"
]

NAK_TO_RASHI_MAP = {
    0: [0], 1: [0], 2: [0, 1], 3: [1], 4: [1, 2], 5: [2], 
    6: [2, 3], 7: [3], 8: [3], 9: [4], 10: [4], 11: [4, 5], 
    12: [5], 13: [5, 6], 14: [6], 15: [6, 7], 16: [7], 17: [7], 
    18: [8], 19: [8], 20: [8, 9], 21: [9], 22: [9, 10], 23: [10], 
    24: [10, 11], 25: [11], 26: [11]
}

SUN_TRANSIT_DATES = {
    0: "Apr 14 - May 14", 1: "May 15 - Jun 14", 2: "Jun 15 - Jul 15",
    3: "Jul 16 - Aug 16", 4: "Aug 17 - Sep 16", 5: "Sep 17 - Oct 16",
    6: "Oct 17 - Nov 15", 7: "Nov 16 - Dec 15", 8: "Dec 16 - Jan 13",
    9: "Jan 14 - Feb 12", 10: "Feb 13 - Mar 13", 11: "Mar 14 - Apr 13"
}

# --- LOGIC DATA ---
VARNA_GROUP = [0, 1, 2, 0, 1, 2, 2, 0, 1, 2, 2, 0]
VASHYA_GROUP = [0, 0, 1, 2, 1, 1, 1, 3, 1, 2, 1, 2]
YONI_ID = [0, 1, 2, 3, 3, 4, 5, 2, 5, 6, 6, 7, 8, 9, 8, 9, 10, 10, 4, 11, 12, 11, 13, 0, 13, 7, 1]
YONI_Enemy_Map = {0:8, 1:13, 2:11, 3:12, 4:10, 5:6, 6:5, 7:9, 8:0, 9:7, 10:4, 11:2, 12:3, 13:1}
RASHI_LORDS = [2, 5, 3, 1, 0, 3, 5, 2, 4, 6, 6, 4] 
MAITRI_TABLE = [
    [5, 5, 5, 4, 5, 0, 0], [5, 5, 4, 1, 4, 1, 1], [5, 4, 5, 0.5, 5, 3, 0.5],
    [4, 1, 0.5, 5, 0.5, 5, 4], [5, 4, 5, 0.5, 5, 0.5, 3], [0, 1, 3, 5, 0.5, 5, 5], [0, 1, 0.5, 4, 3, 5, 5]
]
GANA_TYPE = [0, 1, 2, 1, 0, 1, 0, 0, 2, 2, 1, 1, 0, 2, 0, 2, 0, 2, 2, 1, 1, 0, 2, 2, 1, 1, 0]
NADI_TYPE = [0, 1, 2, 2, 1, 0, 0, 1, 2, 0, 1, 2, 2, 1, 0, 0, 1, 2, 0, 1, 2, 2, 1, 0, 0, 1, 2]

# --- HELPERS ---
@st.cache_resource
def get_geolocator():
    return Nominatim(user_agent="vedic_matcher_v6_gemini_fix", timeout=10)

@st.cache_resource
def get_tf():
    return TimezoneFinder()

def get_offset_smart(city, country, dt, manual_tz):
    geolocator = get_geolocator()
    tf = get_tf()
    try:
        loc = geolocator.geocode(f"{city}, {country}")
        if loc:
            tz_name = tf.timezone_at(lng=loc.longitude, lat=loc.latitude)
            if tz_name:
                timezone = pytz.timezone(tz_name)
                localized_dt = timezone.localize(dt)
                return localized_dt.utcoffset().total_seconds() / 3600.0, f"📍 Found: {city} ({tz_name})"
        raise ValueError("City not found")
    except:
        return manual_tz, f"⚠️ Using Manual TZ: {manual_tz}"

def get_planetary_positions(date_obj, time_obj, city, country, manual_tz):
    dt = datetime.datetime.combine(date_obj, time_obj)
    offset, msg = get_offset_smart(city, country, dt, manual_tz)
    
    obs = ephem.Observer()
    obs.date = dt - datetime.timedelta(hours=offset)
    
    # MOON
    moon = ephem.Moon()
    moon.compute(obs)
    ecl_moon = ephem.Ecliptic(moon)
    
    # MARS
    mars = ephem.Mars()
    mars.compute(obs)
    ecl_mars = ephem.Ecliptic(mars)
    
    ayanamsa = 23.85 + (dt.year - 2000) * 0.01396
    
    sidereal_moon = (math.degrees(ecl_moon.lon) - ayanamsa) % 360
    sidereal_mars = (math.degrees(ecl_mars.lon) - ayanamsa) % 360
    
    return sidereal_moon, sidereal_mars, msg

def get_nak_rashi(long):
    return int(long / 13.333333), int(long / 30)

def check_mars_dosha_from_moon(moon_rashi, mars_long):
    mars_rashi = int(mars_long / 30)
    house_diff = (mars_rashi - moon_rashi) % 12 + 1
    if house_diff in [2, 4, 7, 8, 12]:
        return True, f"Present (House {house_diff})"
    return False, "Absent"

def get_jupiter_position_for_year(year):
    dt = datetime.date(year, 7, 1)
    obs = ephem.Observer()
    obs.date = dt
    jupiter = ephem.Jupiter()
    jupiter.compute(obs)
    ecl = ephem.Ecliptic(jupiter)
    ayanamsa = 23.85 + (year - 2000) * 0.01396
    sidereal_long = (math.degrees(ecl.lon) - ayanamsa) % 360
    return int(sidereal_long / 30)

def predict_marriage_luck_years(rashi_idx):
    predictions = []
    check_years = [2025, 2026, 2027]
    for year in check_years:
        jup_rashi = get_jupiter_position_for_year(year)
        diff = (jup_rashi - rashi_idx) % 12
        house = diff + 1
        if house in [2, 5, 7, 9, 11]:
            predictions.append((year, "✨ Excellent Year", "Jupiter in House " + str(house)))
        else:
            predictions.append((year, "Neutral Year", "Jupiter in House " + str(house)))
    return predictions

def predict_wedding_month(rashi_idx):
    h = 7
    target_rashi = (rashi_idx + h - 1) % 12
    return SUN_TRANSIT_DATES[target_rashi]

def create_gauge(score):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = score,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Compatibility Score"},
        gauge = {
            'axis': {'range': [None, 36], 'tickwidth': 1, 'tickcolor': "darkblue"},
            'bar': {'color': "rgba(0,0,0,0)"},
            'steps': [
                {'range': [0, 18], 'color': "#ffcccb"},  
                {'range': [18, 25], 'color': "#ffffcc"}, 
                {'range': [25, 36], 'color': "#90ee90"} 
            ],
            'threshold': {'line': {'color': "black", 'width': 4}, 'thickness': 0.75, 'value': score}
        }
    ))
    fig.update_layout(height=250, margin=dict(l=10, r=10, t=40, b=10))
    return fig

def create_report_text(boy_name, girl_name, score, rajju, vedha, b_prof, g_prof):
    txt = f"""
    VEDIC MATCHER PRO - COMPATIBILITY REPORT
    ----------------------------------------
    Date: {datetime.date.today()}
    
    BOY: {boy_name}
    Traits: {b_prof['Symbol']} | {b_prof['Animal']} | {b_prof['Trait']}
    
    GIRL: {girl_name}
    Traits: {g_prof['Symbol']} | {g_prof['Animal']} | {g_prof['Trait']}
    
    ----------------------------------------
    FINAL SCORE: {score} / 36
    ----------------------------------------
    """
    return txt

def calculate_all(b_nak, b_rashi, g_nak, g_rashi):
    score = 0
    breakdown = []
    
    varna = 1 if VARNA_GROUP[b_rashi] <= VARNA_GROUP[g_rashi] else 0
    score += varna
    breakdown.append(("🧠 Varna (Ego)", varna, 1))
    
    vashya = 0
    if VASHYA_GROUP[b_rashi] == VASHYA_GROUP[g_rashi]: vashya = 2
    elif (VASHYA_GROUP[b_rashi] == 0 and VASHYA_GROUP[g_rashi] == 1) or \
         (VASHYA_GROUP[b_rashi] == 1 and VASHYA_GROUP[g_rashi] == 0): vashya = 1 
    elif VASHYA_GROUP[b_rashi] != VASHYA_GROUP[g_rashi]: vashya = 0.5 
    score += vashya
    breakdown.append(("🧲 Vashya (Attraction)", vashya, 2))
    
    count = (b_nak - g_nak) % 27 + 1
    tara = 3 if count % 9 not in [3, 5, 7] else 0 
    score += tara
    breakdown.append(("✨ Tara (Destiny)", tara, 3))
    
    id_b, id_g = YONI_ID[b_nak], YONI_ID[g_nak]
    if id_b == id_g: yoni = 4
    elif YONI_Enemy_Map[id_b] == id_g or YONI_Enemy_Map[id_g] == id_b: yoni = 0
    else: yoni = 2 
    score += yoni
    breakdown.append(("🦁 Yoni (Intimacy)", yoni, 4))
    
    lb, lg = RASHI_LORDS[b_rashi], RASHI_LORDS[g_rashi]
    maitri = MAITRI_TABLE[lb][lg]
    score += maitri
    breakdown.append(("🤝 Maitri (Friendship)", maitri, 5))
    
    gb, gg = GANA_TYPE[b_nak], GANA_TYPE[g_nak]
    if gb == gg: gana = 6
    elif (gg==0 and gb==2) or (gg==2 and gb==0): gana = 1 
    elif (gg==1 and gb==2) or (gg==2 and gb==1): gana = 0 
    else: gana = 5 
    score += gana
    breakdown.append(("🎭 Gana (Temperament)", gana, 6))
    
    dist = (b_rashi - g_rashi) % 12
    bhakoot = 7
    if dist in [1, 11, 4, 8, 5, 7]: bhakoot = 0
    if bhakoot == 0 and maitri >= 4: bhakoot = 7 
    score += bhakoot
    breakdown.append(("💘 Bhakoot (Love)", bhakoot, 7))
    
    nb, ng = NADI_TYPE[b_nak], NADI_TYPE[g_nak]
    nadi = 8
    nadi_msg = "OK"
    if nb == ng: 
        nadi = 0
        nadi_msg = "Dosha (0 Pts)"
        if b_nak == g_nak:
            if NAKSHATRAS[b_nak] in SAME_NAKSHATRA_ALLOWED:
                nadi = 8; nadi_msg = "Exception: Allowed Star"
            else:
                nadi = 0; nadi_msg = "Dosha (Same Star)"
        elif b_rashi == g_rashi or maitri >= 4:
            nadi = 8; nadi_msg = "Cancelled (Friend/Rashi)"
            
    score += nadi
    breakdown.append(("🧬 Nadi (Health)", nadi, 8))
    
    rajju_group = [0, 1, 2, 3, 4, 3, 2, 1, 0] * 3
    vedha_pairs = {0: 17, 1: 16, 2: 15, 3: 14, 4: 22, 5: 21, 6: 20, 7: 19, 8: 18, 9: 26, 10: 25, 11: 24, 12: 23, 13: 13}
    for k, v in list(vedha_pairs.items()): vedha_pairs[v] = k

    rajju_status = "Pass"
    if rajju_group[b_nak] == rajju_group[g_nak]:
        if maitri >= 4 or b_rashi == g_rashi: rajju_status = "Cancelled"
        else: rajju_status = "Fail"

    vedha_status = "Pass"
    if vedha_pairs.get(g_nak) == b_nak: vedha_status = "Fail"
        
    return score, breakdown, rajju_status, vedha_status, nadi_msg

def calculate_advanced(b_nak, g_nak):
    count = (b_nak - g_nak) % 27 + 1
    mahendra = "Standard (Neutral)"
    if count in [4, 7, 10, 13, 16, 19, 22, 25]: mahendra = "Present ✅"
    dist = (b_nak - g_nak) % 27
    stree_deergha = "Average (Neutral)"
    if dist > 13: stree_deergha = "Excellent ✅"
    elif dist > 7: stree_deergha = "Good"
    return mahendra, stree_deergha

# --- UI ---
st.title("🕉️ Vedic Matcher Pro")
st.markdown("Advanced Compatibility: Ashta Koota + South Indian Checks + AI Wedding Guru.")

mode = st.radio("Choose Input Mode:", ["Use Birth Details", "Direct Star Entry"], horizontal=True)

if mode == "Use Birth Details":
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Boy Details")
        b_date = st.date_input("Boy Date", datetime.date(1995, 1, 1))
        b_time = st.time_input("Boy Time", datetime.time(10, 0), step=60)
        b_city = st.text_input("Boy City", "Hyderabad")
        b_country = st.text_input("Boy Country", "India")
        with st.expander("Advanced: Manual Timezone"):
             b_tz = st.number_input("Boy Manual UTC Offset", 5.5)
    with c2:
        st.subheader("Girl Details")
        g_date = st.date_input("Girl Date", datetime.date(1994, 11, 28))
        g_time = st.time_input("Girl Time", datetime.time(7, 30), step=60)
        g_city = st.text_input("Girl City", "Hyderabad")
        g_country = st.text_input("Girl Country", "India")
        with st.expander("Advanced: Manual Timezone"):
             g_tz = st.number_input("Girl Manual UTC Offset", 5.5)

elif mode == "Direct Star Entry":
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Boy Details")
        b_star = st.selectbox("Boy Star", NAKSHATRAS, index=0)
        b_idx = NAKSHATRAS.index(b_star)
        b_poss = NAK_TO_RASHI_MAP[b_idx]
        b_opts = [RASHIS[i] for i in b_poss]
        b_rashi_sel = st.selectbox("Boy Rashi", b_opts)
        b_mars_dosha = (False, "Unknown (Need Birth Date)")
        
    with c2:
        st.subheader("Girl Details")
        g_star = st.selectbox("Girl Star", NAKSHATRAS, index=11)
        g_idx = NAKSHATRAS.index(g_star)
        g_poss = NAK_TO_RASHI_MAP[g_idx]
        g_opts = [RASHIS[i] for i in g_poss]
        kanya_default = 0
        if "Virgo (Kanya)" in g_opts: kanya_default = g_opts.index("Virgo (Kanya)")
        g_rashi_sel = st.selectbox("Girl Rashi", g_opts, index=kanya_default)
        g_mars_dosha = (False, "Unknown (Need Birth Date)")

if st.button("Calculate Match", type="primary"):
    try:
        if mode == "Use Birth Details":
            with st.spinner("Calculating planetary positions..."):
                b_moon_long, b_mars_long, b_msg = get_planetary_positions(b_date, b_time, b_city, b_country, b_tz)
                g_moon_long, g_mars_long, g_msg = get_planetary_positions(g_date, g_time, g_city, g_country, g_tz)
                
                if b_moon_long is None: st.error("Location error."); st.stop()
                b_nak, b_rashi = get_nak_rashi(b_moon_long)
                g_nak, g_rashi = get_nak_rashi(g_moon_long)
                b_mars_dosha = check_mars_dosha_from_moon(b_rashi, b_mars_long)
                g_mars_dosha = check_mars_dosha_from_moon(g_rashi, g_mars_long)
                st.success(f"Locations Found! Boy: {b_msg} | Girl: {g_msg}")
        else:
            b_nak = NAKSHATRAS.index(b_star)
            b_rashi = RASHIS.index(b_rashi_sel)
            g_nak = NAKSHATRAS.index(g_star)
            g_rashi = RASHIS.index(g_rashi_sel)
            b_mars_dosha = (False, "Unknown (Direct Mode)")
            g_mars_dosha = (False, "Unknown (Direct Mode)")

        score, breakdown, rajju_status, vedha_status, nadi_msg = calculate_all(b_nak, b_rashi, g_nak, g_rashi)
        mahendra, stree_deergha = calculate_advanced(b_nak, g_nak)
        
        # PROFILES
        b_prof = NAK_TRAITS.get(b_nak, {"Symbol":"-", "Animal":"-", "Trait":"-"})
        g_prof = NAK_TRAITS.get(g_nak, {"Symbol":"-", "Animal":"-", "Trait":"-"})

        # SAVE TO SESSION
        st.session_state.results = {
            "score": score,
            "b_nak": NAKSHATRAS[b_nak],
            "g_nak": NAKSHATRAS[g_nak],
            "b_rashi": RASHIS[b_rashi],
            "g_rashi": RASHIS[g_rashi],
            "rajju": rajju_status,
            "vedha": vedha_status,
            "breakdown": breakdown,
            "nadi_msg": nadi_msg,
            "b_mars": b_mars_dosha,
            "g_mars": g_mars_dosha,
            "mahendra": mahendra,
            "stree": stree_deergha,
            "b_prof": b_prof,
            "g_prof": g_prof,
            "b_rashi_idx": b_rashi,
            "g_rashi_idx": g_rashi
        }
        st.session_state.calculated = True
        
    except Exception as e:
        st.error(f"An error occurred: {e}")

# --- DISPLAY RESULTS (PERSISTENT) ---
if st.session_state.calculated:
    res = st.session_state.results
    
    st.divider()
    
    # PERSONALITY SECTION
    st.subheader("🎭 Personality & Match Profile")
    # [Visual: Zodiac Wheel Placeholder]
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"**BOY: {res['b_nak']}**")
        st.markdown(f"**Symbol:** {res['b_prof']['Symbol']}")
        st.markdown(f"**Animal:** {res['b_prof']['Animal']}")
        st.markdown(f"**Key Trait:** *{res['b_prof']['Trait']}*")
    with col2:
        st.info(f"**GIRL: {res['g_nak']}**")
        st.markdown(f"**Symbol:** {res['g_prof']['Symbol']}")
        st.markdown(f"**Animal:** {res['g_prof']['Animal']}")
        st.markdown(f"**Key Trait:** *{res['g_prof']['Trait']}*")

    # DOWNLOAD
    report_str = create_report_text(res['b_nak'], res['g_nak'], res['score'], res['rajju'], res['vedha'], res['b_prof'], res['g_prof'])
    st.download_button("📥 Download Match Report", report_str, file_name="Vedic_Match_Report.txt")

    st.divider()
    
    # SCORE GAUGE
    st.plotly_chart(create_gauge(res['score']), use_container_width=True)
    
    # VERDICT
    critical_fail = False
    if res['rajju'] == "Fail" or res['vedha'] == "Fail":
        st.error("⚠️ **Compatibility Alignment Check Required**")
        st.info("Incompatibilities detected (Rajju/Vedha). Professional consultation recommended.")
        critical_fail = True
    elif res['rajju'] == "Cancelled":
        st.warning("⚠️ Incompatibilities detected but neutralized (Planetary Friendship).")
        
    if not critical_fail:
        if res['score'] >= 25: st.success("✅ EXCELLENT MATCH")
        elif res['score'] >= 18: st.success("✅ GOOD MATCH")
        else: st.warning("⚠️ NOT RECOMMENDED (Score too low)")
    
    # TABS
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Breakdown", "🪐 Mars & Bonus", "🔮 Timing", "💬 AI Guru"])
    
    with tab1:
        df = pd.DataFrame(res['breakdown'], columns=["Koota", "Points", "Max"])
        df['Points'] = df['Points'].apply(lambda x: f"{x:g}")
        st.table(df)
        if "Cancelled" in res['nadi_msg']: st.caption(f"ℹ️ Nadi Status: {res['nadi_msg']}")

    with tab2:
        st.markdown("### 🪐 Mars Dosha Check (From Moon)")
        m_data = []
        if res['b_mars'][0]: m_data.append(["Boy", "Possible Dosha ⚠️", res['b_mars'][1]])
        else: m_data.append(["Boy", "No Dosha ✅", "Safe"])
        if res['g_mars'][0]: m_data.append(["Girl", "Possible Dosha ⚠️", res['g_mars'][1]])
        else: m_data.append(["Girl", "No Dosha ✅", "Safe"])
        st.table(pd.DataFrame(m_data, columns=["Person", "Status", "Details"]))
        
        st.markdown("### ✨ Bonus Factors")
        chk_data = [("Mahendra", res['mahendra'], "Attachment"), ("Stree Deergha", res['stree'], "Wellbeing")]
        st.table(pd.DataFrame(chk_data, columns=["Factor", "Status", "Meaning"]))

    with tab3:
        st.markdown("### 🔮 Favorable Years (Jupiter Transit)")
        # [Visual: Planetary Transit Chart Placeholder]
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Boy's Lucky Years:**")
            for y, r, d in predict_marriage_luck_years(res['b_rashi_idx']):
                color = "green" if "Excellent" in r else "grey"
                st.markdown(f"- **{y}:** :{color}[{r}]")
        with c2:
            st.markdown("**Girl's Lucky Years:**")
            for y, r, d in predict_marriage_luck_years(res['g_rashi_idx']):
                color = "green" if "Excellent" in r else "grey"
                st.markdown(f"- **{y}:** :{color}[{r}]")
        
        st.divider()
        st.markdown("### 💍 Best Wedding Month (Recurring Annually)")
        mc1, mc2 = st.columns(2)
        mc1.markdown(f"**Boy:** {predict_wedding_month(res['b_rashi_idx'])}")
        mc2.markdown(f"**Girl:** {predict_wedding_month(res['g_rashi_idx'])}")

    with tab4:
        st.markdown("### 🤖 Chat with Wedding Guru (Powered by Gemini)")
        if not api_key:
            st.warning("Please enter your Gemini API Key in the Sidebar to use this feature.")
        else:
            # Display chat history
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            # Input
            if prompt := st.chat_input("Ask about remedies, rituals, or dates..."):
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)

                with st.chat_message("assistant"):
                    with st.spinner("Guru-ji is thinking..."):
                        try:
                            # Configure model
                            model = genai.GenerativeModel('gemini-1.5-flash')
                            
                            # Construct context
                            system_context = f"""
                            You are a wise Vedic Wedding Assistant.
                            Match Context: Boy ({res['b_nak']}, {res['b_rashi']}) & Girl ({res['g_nak']}, {res['g_rashi']}).
                            Score: {res['score']}/36. Doshas: Rajju ({res['rajju']}), Vedha ({res['vedha']}).
                            Traits: Boy is {res['b_prof']['Trait']}, Girl is {res['g_prof']['Trait']}.
                            Answer concisely about rituals, remedies, and wedding planning.
                            """
                            
                            # Build History
                            history = []
                            history.append({"role": "user", "parts": [system_context]})
                            history.append({"role": "model", "parts": ["I understand. I am ready to assist with Vedic wedding advice."]})
                            
                            for m in st.session_state.messages:
                                role = "user" if m["role"] == "user" else "model"
                                history.append({"role": role, "parts": [m["content"]]})
                                
                            chat = model.start_chat(history=history[:-1])
                            response = chat.send_message(prompt, stream=True)
                            
                            full_response = ""
                            placeholder = st.empty()
                            for chunk in response:
                                full_response += chunk.text
                                placeholder.markdown(full_response)
                                
                            st.session_state.messages.append({"role": "assistant", "content": full_response})
                            
                        except Exception as e:
                            st.error(f"Error: {e}")

# --- INFO ---
st.divider()
with st.expander("ℹ️ How this App Works"):
    st.markdown("""
    **1. South Indian Checks:** Checks **Rajju** (Body Compatibility) & **Vedha**. 
    **2. Score:** 36 Point system.
    **3. Mars Check:** Checks Mars position from Moon.
    """)
