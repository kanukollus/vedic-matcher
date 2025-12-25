import streamlit as st
import ephem
import datetime
import math
import pytz
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
import pandas as pd

# --- PAGE CONFIG ---
st.set_page_config(page_title="Vedic Matcher", page_icon="🕉️", layout="centered")

# --- DATA CONSTANTS ---
NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta",
    "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
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
    return Nominatim(user_agent="vedic_streamlit_app_v1", timeout=10)

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
                return localized_dt.utcoffset().total_seconds() / 3600.0, f"📍 Found: {city}"
        raise ValueError("City not found")
    except:
        return manual_tz, f"⚠️ Using Manual TZ: {manual_tz}"

def get_sidereal_moon(date_obj, time_obj, city, country, manual_tz):
    dt = datetime.datetime.combine(date_obj, time_obj)
    offset, msg = get_offset_smart(city, country, dt, manual_tz)
    
    obs = ephem.Observer()
    obs.date = dt - datetime.timedelta(hours=offset)
    moon = ephem.Moon()
    moon.compute(obs)
    ecl = ephem.Ecliptic(moon)
    
    ayanamsa = 23.85 + (dt.year - 2000) * 0.01396
    sidereal_long = (math.degrees(ecl.lon) - ayanamsa) % 360
    return sidereal_long, msg

def get_nak_rashi(long):
    return int(long / 13.333333), int(long / 30)

def calculate_all(b_nak, b_rashi, g_nak, g_rashi):
    score = 0
    breakdown = []
    
    # Calc Logic (Same as before)
    varna = 1 if VARNA_GROUP[b_rashi] <= VARNA_GROUP[g_rashi] else 0
    score += varna
    breakdown.append(("Varna", varna, 1))
    
    vashya = 2 if VASHYA_GROUP[b_rashi] == VASHYA_GROUP[g_rashi] else 0.5
    score += vashya
    breakdown.append(("Vashya", vashya, 2))
    
    count = (b_nak - g_nak) % 27 + 1
    tara = 3 if count % 9 not in [3, 5, 7] else 0 
    score += tara
    breakdown.append(("Tara", tara, 3))
    
    id_b, id_g = YONI_ID[b_nak], YONI_ID[g_nak]
    if id_b == id_g: yoni = 4
    elif YONI_Enemy_Map[id_b] == id_g or YONI_Enemy_Map[id_g] == id_b: yoni = 0
    else: yoni = 2 
    score += yoni
    breakdown.append(("Yoni", yoni, 4))
    
    lb, lg = RASHI_LORDS[b_rashi], RASHI_LORDS[g_rashi]
    maitri = MAITRI_TABLE[lb][lg]
    score += maitri
    breakdown.append(("Maitri", maitri, 5))
    
    gb, gg = GANA_TYPE[b_nak], GANA_TYPE[g_nak]
    if gb == gg: gana = 6
    elif (gg==0 and gb==2) or (gg==2 and gb==0): gana = 1 
    elif (gg==1 and gb==2) or (gg==2 and gb==1): gana = 0 
    else: gana = 5 
    score += gana
    breakdown.append(("Gana", gana, 6))
    
    dist = (b_rashi - g_rashi) % 12
    bhakoot = 7
    if dist in [1, 11, 4, 8, 5, 7]: bhakoot = 0
    if bhakoot == 0 and maitri >= 4: bhakoot = 7 # Exception
    score += bhakoot
    breakdown.append(("Bhakoot", bhakoot, 7))
    
    nb, ng = NADI_TYPE[b_nak], NADI_TYPE[g_nak]
    nadi = 8
    if nb == ng: nadi = 0
    if nadi == 0 and b_rashi == g_rashi and b_nak != g_nak: nadi = 8 # Exception
    score += nadi
    breakdown.append(("Nadi", nadi, 8))
    
    rajju_group = [0, 1, 2, 3, 4, 3, 2, 1, 0] * 3
    vedha_pairs = {0: 17, 1: 16, 2: 15, 3: 14, 4: 22, 5: 21, 6: 20, 7: 19, 8: 18, 9: 26, 10: 25, 11: 24, 12: 23, 13: 13}
    for k, v in list(vedha_pairs.items()): vedha_pairs[v] = k

    rajju_fail = rajju_group[b_nak] == rajju_group[g_nak]
    vedha_fail = vedha_pairs.get(g_nak) == b_nak
    
    return score, breakdown, rajju_fail, vedha_fail

# --- UI ---
st.title("🕉️ Vedic Matcher")
st.markdown("Calculate compatibility using Ashta Koota (36 Points) + South Indian Dosha Check.")

mode = st.radio("Choose Input Mode:", ["Use Birth Details", "Direct Star Entry"], horizontal=True)

if mode == "Use Birth Details":
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Boy Details")
        b_date = st.date_input("Boy Date", datetime.date(1995, 1, 1))
        b_time = st.time_input("Boy Time", datetime.time(10, 0))
        b_city = st.text_input("Boy City", "Edison")
        b_country = st.text_input("Boy Country", "USA")
        b_tz = st.number_input("Boy Backup TZ", -5.0)
    with c2:
        st.subheader("Girl Details")
        g_date = st.date_input("Girl Date", datetime.date(1994, 11, 28))
        g_time = st.time_input("Girl Time", datetime.time(7, 30))
        g_city = st.text_input("Girl City", "Hyderabad")
        g_country = st.text_input("Girl Country", "India")
        g_tz = st.number_input("Girl Backup TZ", 5.5)

elif mode == "Direct Star Entry":
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Boy Details")
        b_star = st.selectbox("Boy Star", NAKSHATRAS, index=0)
        # Smart Rashi Logic Boy
        b_idx = NAKSHATRAS.index(b_star)
        b_poss = NAK_TO_RASHI_MAP[b_idx]
        b_opts = [RASHIS[i] for i in b_poss]
        b_rashi_sel = st.selectbox("Boy Rashi", b_opts)
    with c2:
        st.subheader("Girl Details")
        g_star = st.selectbox("Girl Star", NAKSHATRAS, index=11) # Uttara Phalguni
        # Smart Rashi Logic Girl
        g_idx = NAKSHATRAS.index(g_star)
        g_poss = NAK_TO_RASHI_MAP[g_idx]
        g_opts = [RASHIS[i] for i in g_poss]
        g_rashi_sel = st.selectbox("Girl Rashi", g_opts)

if st.button("Calculate Match", type="primary"):
    try:
        if mode == "Use Birth Details":
            with st.spinner("Calculating planetary positions..."):
                b_long, b_msg = get_sidereal_moon(b_date, b_time, b_city, b_country, b_tz)
                g_long, g_msg = get_sidereal_moon(g_date, g_time, g_city, g_country, g_tz)
                
                if b_long is None or g_long is None:
                    st.error("Invalid Date/Time or Location not found.")
                    st.stop()
                
                b_nak, b_rashi = get_nak_rashi(b_long)
                g_nak, g_rashi = get_nak_rashi(g_long)
                st.success(f"Locations Found! Boy: {b_msg} | Girl: {g_msg}")
        else:
            b_nak = NAKSHATRAS.index(b_star)
            b_rashi = RASHIS.index(b_rashi_sel)
            g_nak = NAKSHATRAS.index(g_star)
            g_rashi = RASHIS.index(g_rashi_sel)

        # Calculate
        score, breakdown, rajju_fail, vedha_fail = calculate_all(b_nak, b_rashi, g_nak, g_rashi)
        
        st.divider()
        col1, col2 = st.columns(2)
        col1.info(f"**Boy:** {NAKSHATRAS[b_nak]} | {RASHIS[b_rashi]}")
        col2.info(f"**Girl:** {NAKSHATRAS[g_nak]} | {RASHIS[g_rashi]}")
        
        # Display Score
        st.subheader(f"Score: {score} / 36")
        st.progress(score/36)
        
        # Verdict
        if rajju_fail:
            st.error("❌ DO NOT PROCEED: Critical Rajju Dosha Detected.")
        elif vedha_fail:
            st.error("❌ DO NOT PROCEED: Critical Vedha Dosha Detected.")
        else:
            if score >= 25:
                st.success("✅ EXCELLENT MATCH (Highly Recommended)")
            elif score >= 18:
                st.success("✅ GOOD MATCH (Proceed)")
            else:
                st.warning("⚠️ NOT RECOMMENDED (Score too low)")
        
        with st.expander("See Detailed Breakdown"):
            df = pd.DataFrame(breakdown, columns=["Koota", "Points", "Max"])
            st.table(df)
            
    except Exception as e:
        st.error(f"An error occurred: {e}")
