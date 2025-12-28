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
import time

# --- PAGE CONFIG ---
st.set_page_config(page_title="Vedic Matcher Pro", page_icon="🕉️", layout="centered")

# --- CSS STYLING ---
st.markdown("""
<style>
    .guna-card { background-color: #f0f2f6; color: #31333F; padding: 15px; border-radius: 10px; margin-bottom: 10px; border-left: 5px solid #ccc; }
    .guna-header { font-size: 18px; font-weight: bold; display: flex; justify-content: space-between; color: #31333F; }
    .guna-score { font-weight: bold; }
    .guna-reason { font-size: 14px; color: #555; margin-top: 5px; font-style: italic; }
    .border-green { border-left-color: #00cc00 !important; }
    .border-orange { border-left-color: #ffa500 !important; }
    .border-red { border-left-color: #ff4b4b !important; }
    .text-green { color: #00cc00 !important; }
    .text-orange { color: #ffa500 !important; }
    .text-red { color: #ff4b4b !important; }
    .chart-container { display: grid; grid-template-columns: repeat(4, 1fr); grid-template-rows: repeat(4, 60px); gap: 2px; background-color: #444; border: 2px solid #333; width: 100%; max-width: 350px; margin: auto; font-size: 10px; }
    .chart-box { background-color: #fffbe6; color: #000; display: flex; align-items: center; justify-content: center; text-align: center; font-weight: bold; padding: 2px; border: 1px solid #ccc; }
    .chart-center { grid-column: 2 / 4; grid-row: 2 / 4; background-color: #fff; display: flex; flex-direction: column; align-items: center; justify-content: center; font-size: 14px; color: #555; }
    .verdict-box { background-color: #e8f5e9; border: 1px solid #c8e6c9; padding: 20px; border-radius: 10px; margin-top: 20px; color: #1b5e20; }
    .verdict-title { font-size: 20px; font-weight: bold; margin-bottom: 10px; display: flex; align-items: center; gap: 10px; }
</style>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
if "calculated" not in st.session_state: st.session_state.calculated = False
if "results" not in st.session_state: st.session_state.results = {}
if "messages" not in st.session_state: st.session_state.messages = []
if "input_mode" not in st.session_state: st.session_state.input_mode = "Birth Details"
if "api_key" not in st.session_state: st.session_state.api_key = ""

# --- DATA ---
NAKSHATRAS = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra","Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni","Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha","Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta","Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"]
RASHIS = ["Aries (Mesha)", "Taurus (Vrishabha)", "Gemini (Mithuna)", "Cancer (Karka)","Leo (Simha)", "Virgo (Kanya)", "Libra (Tula)", "Scorpio (Vrishchika)","Sagittarius (Dhanu)", "Capricorn (Makara)", "Aquarius (Kumbha)", "Pisces (Meena)"]
SOUTH_CHART_MAP = {11: 0, 0: 1, 1: 2, 2: 3, 10: 4, 3: 7, 9: 8, 4: 11, 8: 12, 7: 13, 6: 14, 5: 15}
NAK_TO_RASHI_MAP = {0: [0], 1: [0], 2: [0, 1], 3: [1], 4: [1, 2], 5: [2], 6: [2, 3], 7: [3], 8: [3], 9: [4], 10: [4], 11: [4, 5], 12: [5], 13: [5, 6], 14: [6], 15: [6, 7], 16: [7], 17: [7], 18: [8], 19: [8], 20: [8, 9], 21: [9], 22: [9, 10], 23: [10], 24: [10, 11], 25: [11], 26: [11]}
SUN_TRANSIT_DATES = {0: "Apr 14 - May 14", 1: "May 15 - Jun 14", 2: "Jun 15 - Jul 15", 3: "Jul 16 - Aug 16", 4: "Aug 17 - Sep 16", 5: "Sep 17 - Oct 16", 6: "Oct 17 - Nov 15", 7: "Nov 16 - Dec 15", 8: "Dec 16 - Jan 13", 9: "Jan 14 - Feb 12", 10: "Feb 13 - Mar 13", 11: "Mar 14 - Apr 13"}
MAITRI_TABLE = [[5, 5, 5, 4, 5, 0, 0], [5, 5, 4, 1, 4, 1, 1], [5, 4, 5, 0.5, 5, 3, 0.5],[4, 1, 0.5, 5, 0.5, 5, 4], [5, 4, 5, 0.5, 5, 0.5, 3], [0, 1, 3, 5, 0.5, 5, 5], [0, 1, 0.5, 4, 3, 5, 5]]
GANA_TYPE = [0, 1, 2, 1, 0, 1, 0, 0, 2, 2, 1, 1, 0, 2, 0, 2, 0, 2, 2, 1, 1, 0, 2, 2, 1, 1, 0]
GANA_NAMES = ["Deva (Divine)", "Manushya (Human)", "Rakshasa (Demon)"]
NADI_TYPE = [0, 1, 2, 2, 1, 0, 0, 1, 2, 0, 1, 2, 2, 1, 0, 0, 1, 2, 0, 1, 2, 2, 1, 0, 0, 1, 2]
NADI_NAMES = ["Adi (Start)", "Madhya (Middle)", "Antya (End)"]
SAME_NAKSHATRA_ALLOWED = ["Rohini", "Ardra", "Pushya", "Magha", "Vishakha", "Shravana", "Uttara Bhadrapada", "Revati"]
VARNA_GROUP = [0, 1, 2, 0, 1, 2, 2, 0, 1, 2, 2, 0]
VASHYA_GROUP = [0, 0, 1, 2, 1, 1, 1, 3, 1, 2, 1, 2]
YONI_ID = [0, 1, 2, 3, 3, 4, 5, 2, 5, 6, 6, 7, 8, 9, 8, 9, 10, 10, 4, 11, 12, 11, 13, 0, 13, 7, 1]
YONI_Enemy_Map = {0:8, 1:13, 2:11, 3:12, 4:10, 5:6, 6:5, 7:9, 8:0, 9:7, 10:4, 11:2, 12:3, 13:1}
RASHI_LORDS = [2, 5, 3, 1, 0, 3, 5, 2, 4, 6, 6, 4] 
DASHA_ORDER = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
DASHA_YEARS = {"Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7, "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17}
SPECIAL_ASPECTS = {"Mars": [4, 7, 8], "Jupiter": [5, 7, 9], "Saturn": [3, 7, 10], "Rahu": [5, 7, 9], "Ketu": [5, 7, 9]}

# --- HELPER FUNCTIONS ---
@st.cache_resource
def get_geolocator(): return Nominatim(user_agent="vedic_matcher_v61_ai_bridge", timeout=10)
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

def get_planetary_positions(date_obj, time_obj, city, country, detailed=False):
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
    
    chart_data = None
    if detailed:
        bodies = [ephem.Sun(), ephem.Moon(), ephem.Mars(), ephem.Mercury(), ephem.Jupiter(), ephem.Venus(), ephem.Saturn()]
        names = ["Sun", "Moon", "Mars", "Merc", "Jup", "Ven", "Sat"]
        chart_data = {}
        for body, name in zip(bodies, names):
            body.compute(obs)
            long = (math.degrees(ephem.Ecliptic(body).lon) - ayanamsa) % 360
            r_idx = int(long / 30)
            if r_idx not in chart_data: chart_data[r_idx] = []
            chart_data[r_idx].append(name)

    return s_moon, s_mars, s_sun, msg, chart_data

def get_nak_rashi(long): return int(long / 13.333333), int(long / 30)

def check_mars_dosha_smart(moon_rashi, mars_long):
    mars_rashi = int(mars_long / 30)
    house_diff = (mars_rashi - moon_rashi) % 12 + 1
    if house_diff in [2, 4, 7, 8, 12]:
        if mars_rashi == 0 or mars_rashi == 7: return False, f"✅ Balanced (Mars in Own Sign - House {house_diff})"
        elif mars_rashi == 9: return False, f"✅ Balanced (Mars Exalted - House {house_diff})"
        return True, f"🔸 **Active Energy (House {house_diff}):** Mars is strong here. Requires alignment."
    return False, "✨ Calm (Mars is well-placed)"

def render_south_indian_chart(positions, title):
    grid_items = [""] * 16
    for rashi_idx, planets in positions.items():
        if rashi_idx in SOUTH_CHART_MAP:
            short_planets = [p[:2] for p in planets]
            grid_pos = SOUTH_CHART_MAP[rashi_idx]
            grid_items[grid_pos] = "<br>".join(short_planets)
    return f"""
    <div style="text-align: center; margin-bottom: 5px;"><strong>{title}</strong></div>
    <div class="chart-container">
        <div class="chart-box" style="grid-column: 1; grid-row: 1;">{grid_items[0]}<br><span style='font-size:8px; color:grey'>Pisces</span></div>
        <div class="chart-box" style="grid-column: 2; grid-row: 1;">{grid_items[1]}<br><span style='font-size:8px; color:grey'>Aries</span></div>
        <div class="chart-box" style="grid-column: 3; grid-row: 1;">{grid_items[2]}<br><span style='font-size:8px; color:grey'>Taurus</span></div>
        <div class="chart-box" style="grid-column: 4; grid-row: 1;">{grid_items[3]}<br><span style='font-size:8px; color:grey'>Gemini</span></div>
        <div class="chart-box" style="grid-column: 1; grid-row: 2;">{grid_items[4]}<br><span style='font-size:8px; color:grey'>Aquarius</span></div>
        <div class="chart-center"><strong>Rashi<br>Chakra</strong></div>
        <div class="chart-box" style="grid-column: 4; grid-row: 2;">{grid_items[7]}<br><span style='font-size:8px; color:grey'>Cancer</span></div>
        <div class="chart-box" style="grid-column: 1; grid-row: 3;">{grid_items[8]}<br><span style='font-size:8px; color:grey'>Capricorn</span></div>
        <div class="chart-box" style="grid-column: 4; grid-row: 3;">{grid_items[11]}<br><span style='font-size:8px; color:grey'>Leo</span></div>
        <div class="chart-box" style="grid-column: 1; grid-row: 4;">{grid_items[12]}<br><span style='font-size:8px; color:grey'>Sagittarius</span></div>
        <div class="chart-box" style="grid-column: 2; grid-row: 4;">{grid_items[13]}<br><span style='font-size:8px; color:grey'>Scorpio</span></div>
        <div class="chart-box" style="grid-column: 3; grid-row: 4;">{grid_items[14]}<br><span style='font-size:8px; color:grey'>Libra</span></div>
        <div class="chart-box" style="grid-column: 4; grid-row: 4;">{grid_items[15]}<br><span style='font-size:8px; color:grey'>Virgo</span></div>
    </div>"""

def calculate_current_dasha(moon_long, birth_date):
    nak_idx = int(moon_long / 13.333333)
    deg_in_nak = moon_long % 13.333333
    fraction_passed = deg_in_nak / 13.333333
    lord_seq_idx = nak_idx % 9
    start_lord = DASHA_ORDER[lord_seq_idx]
    total_years = DASHA_YEARS[start_lord]
    balance_years = total_years * (1 - fraction_passed)
    current_date = datetime.date.today()
    birth_dt = datetime.date(birth_date.year, birth_date.month, birth_date.day)
    age_days = (current_date - birth_dt).days
    age_years = age_days / 365.25
    curr_lord = start_lord
    rem_balance = balance_years
    if age_years < rem_balance: return curr_lord, "Growth & Foundation"
    age_years -= rem_balance
    curr_idx = lord_seq_idx
    while True:
        curr_idx = (curr_idx + 1) % 9
        curr_lord = DASHA_ORDER[curr_idx]
        years = DASHA_YEARS[curr_lord]
        if age_years < years: break
        age_years -= years
    tones = {
        "Jupiter": "Wisdom & Expansion", "Saturn": "Maturity & Discipline",
        "Mercury": "Communication & Business", "Ketu": "Introspection & Spirituality",
        "Venus": "Love & Comfort", "Sun": "Authority & Career",
        "Moon": "Emotional Depth", "Mars": "Energy & Action",
        "Rahu": "Ambition & Unconventional Growth"
    }
    return curr_lord, tones.get(curr_lord, "General Growth")

def analyze_aspects_and_occupation_rich(chart_data, moon_rashi):
    if not chart_data: return []
    house_7_idx = (moon_rashi + 6) % 12
    observations = []
    occupants = chart_data.get(house_7_idx, [])
    if occupants:
        names = ", ".join(occupants)
        if any(p in ["Sat", "Mars", "Rahu", "Ketu", "Sun"] for p in occupants):
            observations.append(f"⚠️ **{names} in 7th House:** This placement often creates friction or delays in marriage. It requires maturity.")
        elif any(p in ["Jup", "Ven", "Merc"] for p in occupants):
            observations.append(f"✅ **{names} in 7th House:** A blessing. These planets bring natural harmony and affection.")
    aspectors = []
    for r_idx, planets in chart_data.items():
        dist = (house_7_idx - r_idx) % 12 + 1 
        for p in planets:
            if p in SPECIAL_ASPECTS and dist in SPECIAL_ASPECTS[p]: aspectors.append(p)
            elif dist == 7: aspectors.append(p)
    if aspectors:
        aspectors = list(set(aspectors))
        if "Sat" in aspectors: observations.append("ℹ️ **Saturn's Gaze:** Saturn looks at the marriage house. This indicates the relationship will mature slowly.")
        if "Mars" in aspectors: observations.append("🔥 **Mars' Gaze:** Mars adds energy and passion, but arguments can get heated.")
        if "Jup" in aspectors: observations.append("🛡️ **Jupiter's Gaze:** The 'Great Benefic' protects the marriage like a safety net.")
    return observations

def generate_human_verdict(score, rajju, b_obs, g_obs, b_dasha, g_dasha):
    verdict = ""
    if score >= 25: verdict += "Mathematically, this is an **Excellent Match**."
    elif score >= 18: verdict += "Mathematically, this is a **Good Match** compatible for marriage."
    else: verdict += "Mathematically, the compatibility score is on the lower side."
    if rajju == "Fail": verdict += " **Rajju Dosha** suggests paying attention to health/physical compatibility."
    elif rajju == "Cancelled": verdict += " Critical Doshas are effectively **cancelled**."
    verdict += f"\n\n**Time Cycles:** The boy is in a period of *{b_dasha}* and the girl is in *{g_dasha}*. "
    if b_dasha == g_dasha and b_dasha in ["Rahu", "Ketu", "Saturn"]:
        verdict += "Since both are running similar intense periods, mutual patience is key."
    else: verdict += "These periods complement each other well for growth."
    verdict += "\n\n**Planetary Influence:** "
    if any("Aspect" in o for o in b_obs + g_obs):
        verdict += "Planetary aspects on the marriage house indicate a relationship that will mature beautifully with time."
    elif any("Occupants" in o for o in b_obs + g_obs):
        verdict += "Planets occupying the 7th house add specific flavors (energy or wisdom) to the bond."
    else: verdict += "The planetary positions are largely neutral, leaving the relationship's success in your own hands."
    return verdict

def calculate_all(b_nak, b_rashi, g_nak, g_rashi):
    maitri_raw = MAITRI_TABLE[RASHI_LORDS[b_rashi]][RASHI_LORDS[g_rashi]]
    friends = maitri_raw >= 4
    score = 0; bd = []; logs = []
    
    # 1. Varna
    v_raw = 1 if VARNA_GROUP[b_rashi] <= VARNA_GROUP[g_rashi] else 0
    v_final = v_raw; reason = "Natural Match" if v_raw == 1 else "Mismatch"
    if v_raw == 0 and friends: 
        v_final = 1; reason = "Boosted by Maitri"
        logs.append({"Attribute": "Varna", "Problem": "Ego Conflict (0 pts)", "Fix": "Maitri: Rashi Lords are friends.", "Source": "Muhurtha Chintamani"})
    score += v_final; bd.append(("Varna", v_raw, v_final, 1, reason))
    
    # 2. Vashya
    va_raw = 0
    if VASHYA_GROUP[b_rashi] == VASHYA_GROUP[g_rashi]: va_raw = 2
    elif (VASHYA_GROUP[b_rashi] == 0 and VASHYA_GROUP[g_rashi] == 1) or (VASHYA_GROUP[b_rashi] == 1 and VASHYA_GROUP[g_rashi] == 0): va_raw = 1 
    elif VASHYA_GROUP[b_rashi] != VASHYA_GROUP[g_rashi]: va_raw = 0.5 
    va_final = va_raw; reason = "Magnetic" if va_raw >= 1 else "Mismatch"
    if va_raw < 2 and (friends or YONI_ID[b_nak]==YONI_ID[g_nak]): 
        va_final = 2; reason = "Boosted by Maitri/Yoni"
        logs.append({"Attribute": "Vashya", "Problem": f"Attraction Mismatch ({va_raw} pts)", "Fix": "Maitri/Yoni overrides Vashya.", "Source": "Brihat Parashara"})
    score += va_final; bd.append(("Vashya", va_raw, va_final, 2, reason))
    
    # 3. Tara
    cnt = (b_nak - g_nak)%27 + 1
    t_raw = 3 if cnt%9 not in [3,5,7] else 0
    t_final = t_raw; reason = "Benefic" if t_raw == 3 else "Malefic"
    if t_raw == 0 and friends: 
        t_final = 3; reason = "Boosted by Maitri"
        logs.append({"Attribute": "Tara", "Problem": "Malefic Star Position (0 pts)", "Fix": "Maitri: Lords are friends.", "Source": "Muhurtha Martanda"})
    score += t_final; bd.append(("Tara", t_raw, t_final, 3, reason))
    
    # 4. Yoni
    y_raw = 4 if YONI_ID[b_nak] == YONI_ID[g_nak] else (0 if YONI_Enemy_Map.get(YONI_ID[b_nak]) == YONI_ID[g_nak] else 2)
    y_final = y_raw; reason = "Perfect" if y_raw == 4 else "Mismatch"
    if y_raw < 4 and (friends or va_final>=1): 
        y_final = 4; reason = "Compensated by Maitri/Vashya"
        logs.append({"Attribute": "Yoni", "Problem": "Nature Mismatch", "Fix": "Maitri boosts intimacy.", "Source": "Jataka Parijata"})
    score += y_final; bd.append(("Yoni", y_raw, y_final, 4, reason))
    
    # 5. Maitri
    m_final = maitri_raw
    score += m_final; bd.append(("Maitri", maitri_raw, m_final, 5, "Friendly" if maitri_raw>=4 else "Enemy"))
    
    # 6. Gana
    gb, gg = GANA_TYPE[b_nak], GANA_TYPE[g_nak]
    ga_raw = 6 if gb==gg else (0 if (gg==1 and gb==2) or (gg==2 and gb==1) else 1)
    ga_final = ga_raw; reason = "Match" if ga_raw >= 5 else "Mismatch"
    if ga_raw < 6 and friends: 
        ga_final = 6; reason = "Boosted by Maitri"
        logs.append({"Attribute": "Gana", "Problem": f"{GANA_NAMES[gb]} vs {GANA_NAMES[gg]}", "Fix": "Maitri: Lords are friends.", "Source": "Muhurtha Chintamani"})
    score += ga_final; bd.append(("Gana", ga_raw, ga_final, 6, reason))
    
    # 7. Bhakoot
    dist = (b_rashi-g_rashi)%12
    bh_raw = 7 if dist not in [1,11,4,8,5,7] else 0
    bh_final = bh_raw; reason = "Love Flow" if bh_raw == 7 else "Blocked"
    if bh_raw == 0 and (friends or NADI_TYPE[b_nak]!=NADI_TYPE[g_nak]): 
        bh_final = 7; reason = "Compensated by Maitri/Nadi"
        logs.append({"Attribute": "Bhakoot", "Problem": f"Bad Position", "Fix": "Maitri overrides position.", "Source": "Brihat Samhita"})
    score += bh_final; bd.append(("Bhakoot", bh_raw, bh_final, 7, reason))
    
    # 8. Nadi
    n_raw = 8; n_final = 8; n_reason = "Healthy"
    if NADI_TYPE[b_nak] == NADI_TYPE[g_nak]:
        n_raw = 0; n_final = 0; n_reason = "Same Nadi (Dosha)"
        problem = f"{NADI_NAMES[NADI_TYPE[b_nak]]} vs {NADI_NAMES[NADI_TYPE[g_nak]]}"
        if b_nak==g_nak and NAKSHATRAS[b_nak] in SAME_NAKSHATRA_ALLOWED: 
            n_final=8; n_reason="Exception: Allowed Star"
            logs.append({"Attribute": "Nadi", "Problem": problem, "Fix": f"Star {NAKSHATRAS[b_nak]} is an Exception.", "Source": "Classical List"})
        elif b_rashi==g_rashi and b_nak!=g_nak: 
            n_final=8; n_reason="Exception: Same Rashi"
            logs.append({"Attribute": "Nadi", "Problem": problem, "Fix": "Same Rashi, Different Star.", "Source": "Muhurtha Martanda"})
        elif friends: 
            n_final=8; n_reason="Cancelled: Strong Maitri"
            logs.append({"Attribute": "Nadi", "Problem": problem, "Fix": "Maitri overrides Nadi.", "Source": "Muhurtha Chintamani"})
    score += n_final; bd.append(("Nadi", n_raw, n_final, 8, n_reason))

    # South Indian
    rajju_group = [0, 1, 2, 3, 4, 3, 2, 1, 0] * 3
    rajju_status = "Fail" if rajju_group[b_nak] == rajju_group[g_nak] else "Pass"
    if rajju_status == "Fail" and (friends or b_rashi == g_rashi): 
        rajju_status = "Cancelled"
        logs.append({"Attribute": "Rajju", "Problem": "Body Part Clash", "Fix": "Maitri overrides Rajju.", "Source": "Kala Vidhana"})
    
    vedha_pairs = {0: 17, 1: 16, 2: 15, 3: 14, 4: 22, 5: 21, 6: 20, 7: 19, 8: 18, 9: 26, 10: 25, 11: 24, 12: 23, 13: 13}
    for k, v in list(vedha_pairs.items()): vedha_pairs[v] = k
    vedha_status = "Fail" if vedha_pairs.get(g_nak) == b_nak else "Pass"

    return score, bd, logs, rajju_status, vedha_status

def format_chart_for_ai(chart_data):
    if not chart_data: return "Chart not generated."
    readable = []
    for rashi_idx, planets in chart_data.items():
        if planets: readable.append(f"{RASHIS[rashi_idx]}: {', '.join(planets)}")
    return "; ".join(readable)

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

def find_best_matches(source_gender, s_nak, s_rashi):
    matches = []
    for i in range(27):
        target_star_name = NAKSHATRAS[i]
        valid_rashi_indices = NAK_TO_RASHI_MAP[i]
        for r_idx in valid_rashi_indices:
            target_rashi_name = RASHIS[r_idx]
            if source_gender == "Boy": score, bd, logs, _, _ = calculate_all(s_nak, s_rashi, i, r_idx)
            else: score, bd, logs, _, _ = calculate_all(i, r_idx, s_nak, s_rashi)
            raw_score = sum(item[1] for item in bd)
            reason = logs[0]['Fix'] if logs else "Standard Match"
            if score == 36: reason = "Perfect Match!"
            matches.append({"Star": target_star_name, "Rashi": target_rashi_name, "Final Score": score, "Raw Score": raw_score, "Notes": reason})
    return sorted(matches, key=lambda x: x['Final Score'], reverse=True)

# --- STRICT MODEL SELECTION AI HANDLER ---
def handle_ai_query(prompt, context_str, key):
    try:
        genai.configure(api_key=key)
        candidates = ["gemini-1.5-flash"]
        last_err = None
        for m in candidates:
            try:
                model = genai.GenerativeModel(m)
                chat = model.start_chat(history=[{"role": "user", "parts": [context_str]}, {"role": "model", "parts": ["I am your Vedic Astrologer."]}])
                return chat.send_message(prompt).text
            except Exception as e:
                if "429" in str(e): return "⚠️ **Quota Exceeded:** Free AI limit reached. Please wait 60s."
                last_err = str(e)
                continue
        return f"AI Error: {last_err}"
    except Exception as e: return f"Error: {e}"

# --- UI START ---
c_title, c_reset = st.columns([4, 1])
with c_title: st.title("🕉️ Vedic Matcher")
with c_reset:
    if st.button("🔄 Reset"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

tabs = st.tabs(["❤️ Match", "🔍 Find Matches", "💍 Wedding Dates", "🤖 Guru AI"])

# --- TAB 1: MATCH ---
with tabs[0]:
    input_method = st.radio("Mode:", ["Birth Details", "Direct Star Entry"], horizontal=True, key="input_mode")
    pro_mode = False
    
    if input_method == "Birth Details":
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 🤵 Boy")
            b_date = st.date_input("Date", datetime.date(1995,1,1), key="b_d")
            b_time = st.time_input("Time", datetime.time(10,0), step=60, key="b_t")
            b_city = st.text_input("City", "Hyderabad", key="b_c")
        with c2:
            st.markdown("### 👰 Girl")
            g_date = st.date_input("Date", datetime.date(1994,11,28), key="g_d")
            g_time = st.time_input("Time", datetime.time(7,30), step=60, key="g_t")
            g_city = st.text_input("City", "Hyderabad", key="g_c")
        st.markdown("---")
        pro_mode = st.toggle("✨ Generate Full Horoscopes (Pro Feature)")
    else:
        st.info("ℹ️ **Note:** Advanced Horoscope features are available only with full Birth Details.")
        c1, c2 = st.columns(2)
        with c1:
            b_star = st.selectbox("Boy Star", NAKSHATRAS, key="b_s")
            b_rashi_opts = [RASHIS[i] for i in NAK_TO_RASHI_MAP[NAKSHATRAS.index(b_star)]]
            b_rashi_sel = st.selectbox("Boy Rashi", b_rashi_opts, key="b_r")
        with c2:
            # FIX: DEFAULT SELECTION FOR GIRL
            g_star = st.selectbox("Girl Star", NAKSHATRAS, index=11, key="g_s") # 11 is Uttara Phalguni
            g_rashi_opts = [RASHIS[i] for i in NAK_TO_RASHI_MAP[NAKSHATRAS.index(g_star)]]
            try: 
                g_def_idx = next(i for i, r in enumerate(g_rashi_opts) if "Virgo" in r)
            except StopIteration: 
                g_def_idx = 0
            g_rashi_sel = st.selectbox("Girl Rashi", g_rashi_opts, index=g_def_idx, key="g_r")

    if st.button("Check Compatibility", type="primary", use_container_width=True):
        try:
            with st.spinner("Analyzing..."):
                b_planets, g_planets = None, None
                b_dasha_name, b_dasha_tone = "Unknown", ""
                g_dasha_name, g_dasha_tone = "Unknown", ""
                b_mars_result, g_mars_result = ("Skipped", "No Data"), ("Skipped", "No Data")
                
                if input_method == "Birth Details":
                    b_moon, b_mars_l, _, _, b_chart = get_planetary_positions(b_date, b_time, b_city, "India", detailed=pro_mode)
                    g_moon, g_mars_l, _, _, g_chart = get_planetary_positions(g_date, g_time, g_city, "India", detailed=pro_mode)
                    b_nak, b_rashi = get_nak_rashi(b_moon)
                    g_nak, g_rashi = get_nak_rashi(g_moon)
                    b_planets, g_planets = b_chart, g_chart
                    
                    b_mars_result = check_mars_dosha_smart(b_rashi, b_mars_l)
                    g_mars_result = check_mars_dosha_smart(g_rashi, g_mars_l)
                    
                    if pro_mode:
                        b_dasha_name, b_dasha_tone = calculate_current_dasha(b_moon, b_date)
                        g_dasha_name, g_dasha_tone = calculate_current_dasha(g_moon, g_date)
                else:
                    b_nak = NAKSHATRAS.index(b_star); b_rashi = RASHIS.index(b_rashi_sel)
                    g_nak = NAKSHATRAS.index(g_star); g_rashi = RASHIS.index(g_rashi_sel)
                    b_mars = (False, "Unknown"); g_mars = (False, "Unknown")

                score, breakdown, logs, rajju, vedha = calculate_all(b_nak, b_rashi, g_nak, g_rashi)
                
                b_obs, g_obs = [], []
                if pro_mode and b_planets:
                    b_obs = analyze_aspects_and_occupation_rich(b_planets, b_rashi)
                    g_obs = analyze_aspects_and_occupation_rich(g_planets, g_rashi)
                
                human_verdict = generate_human_verdict(score, rajju, b_obs, g_obs, f"{b_dasha_name} ({b_dasha_tone})", f"{g_dasha_name} ({g_dasha_tone})")

                st.session_state.results = {
                    "score": score, "bd": breakdown, "logs": logs, 
                    "b_n": NAKSHATRAS[b_nak], "g_n": NAKSHATRAS[g_nak],
                    "b_mars": b_mars_result, "g_mars": g_mars_result,
                    "rajju": rajju, "vedha": vedha,
                    "b_planets": b_planets, "g_planets": g_planets,
                    "verdict": human_verdict, "b_obs": b_obs, "g_obs": g_obs,
                    "b_dasha": f"{b_dasha_name}", "g_dasha": f"{g_dasha_name}"
                }
                st.session_state.calculated = True
        except Exception as e: st.error(f"Error: {e}")

    if st.session_state.calculated:
        res = st.session_state.results
        st.markdown("---")
        score_val = res['score']; score_color = "#ff4b4b"
        if score_val >= 18: score_color = "#ffa500"
        if score_val >= 25: score_color = "#00cc00"

        c_s, c_g = st.columns([1,1])
        with c_s:
            st.markdown(f"<h1 style='text-align: center; color: {score_color}; margin:0;'>{res['score']}</h1>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center;'>out of 36</p>", unsafe_allow_html=True)
            status = "Excellent Match ✅" if res['score'] > 24 else ("Good Match ⚠️" if res['score'] > 18 else "Not Recommended ❌")
            st.markdown(f"<h3 style='text-align: center; color: {score_color};'>{status}</h3>", unsafe_allow_html=True)
        with c_g:
            fig = go.Figure(go.Indicator(mode = "gauge", value = res['score'], gauge = {'axis': {'range': [0, 36]}, 'bar': {'color': score_color}}))
            fig.update_layout(height=150, margin=dict(l=10, r=10, t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)

        share_text = f"Match Report: {res['b_n']} w/ {res['g_n']}. Score: {res['score']}/36. {status}"
        st.code(share_text, language="text")
        st.caption("👆 Copy to share on WhatsApp")
        
        st.markdown(f"""
        <div class="verdict-box">
            <div class="verdict-title">🤖 AI Astrologer's Verdict</div>
            {res['verdict']}
        </div>
        """, unsafe_allow_html=True)
        
        if st.session_state.api_key:
            if st.button("🤖 Ask AI Guru for Details"):
                with st.spinner("Consulting AI Guru..."):
                    context_str = f"Match Context: Boy {res['b_n']}, Girl {res['g_n']}. Score: {res['score']}."
                    if res.get('b_planets'): context_str += f" Boy Chart: {format_chart_for_ai(res['b_planets'])}."
                    if res.get('g_planets'): context_str += f" Girl Chart: {format_chart_for_ai(res['g_planets'])}."
                    ans = handle_ai_query("Analyze this match in detail.", context_str, st.session_state.api_key)
                    st.session_state.messages.append({"role": "user", "content": "Analyze this match in detail."})
                    st.session_state.messages.append({"role": "assistant", "content": ans})
                    st.toast("✅ Analysis Ready! Switch to the AI Guru tab to read it.")
        else:
            st.info("ℹ️ Enter API Key in 'AI Guru' tab to enable deep analysis.")

        with st.expander("🧠 Show me how I concluded this"):
            st.markdown("### 1. 🤔 Thinking (Analyzing Foundation)")
            st.write(f"I started by calculating the raw Ashta Koota compatibility. The base score was {res['score']}/36.")
            
            st.markdown("### 2. ⚙️ Harnessing (Applying Ancient Rules)")
            if res['logs']:
                st.write(f"I applied **Dosha Bhanga** (cancellation rules) to refine the score:")
                for l in res['logs']: st.caption(f"- {l['Attribute']}: {l['Fix']}")
            else: st.write("No special cancellation rules were needed.")
            
            st.markdown("### 3. ⏱️ Timing (Dasha Sandhi)")
            if "Unknown" not in res['b_dasha']:
                st.write(f"I checked the current Time Cycles (Vimshottari Dasha):")
                st.caption(f"**Boy:** Running {res['b_dasha']}"); st.caption(f"**Girl:** Running {res['g_dasha']}")
            else: st.write("Timing analysis skipped (Basic Mode).")
            
            st.markdown("### 4. 🧵 Stitching (Planetary Context)")
            if res['b_obs'] or res['g_obs']:
                st.write("I analyzed the **Chandra Kundali** for 7th House Aspects (Drishti) & Occupation:")
                if res['b_obs']: st.caption(f"**Boy:** {'; '.join(res['b_obs'])}")
                if res['g_obs']: st.caption(f"**Girl:** {'; '.join(res['g_obs'])}")
            else: st.write("Planetary chart analysis skipped or neutral.")

        if res.get('b_planets') and res.get('g_planets'):
            st.markdown("### 🔮 Pro: Planetary Charts"); c_h1, c_h2 = st.columns(2)
            with c_h1: st.markdown(render_south_indian_chart(res['b_planets'], "Boy's Rashi Chart"), unsafe_allow_html=True)
            with c_h2: st.markdown(render_south_indian_chart(res['g_planets'], "Girl's Rashi Chart"), unsafe_allow_html=True)
        elif input_method == "Birth Details" and not res.get('b_planets'):
            st.info("💡 Tip: Enable 'Generate Full Horoscopes' to see visual charts.")

        st.markdown("### 📋 Quick Scan")
        for item in res['bd']:
            attr, raw, final, max_pts, reason = item
            border_class = "border-green" if final == max_pts else ("border-orange" if final > 0 else "border-red")
            text_class = "text-green" if final == max_pts else ("text-orange" if final > 0 else "text-red")
            st.markdown(f"""<div class="guna-card {border_class}"><div class="guna-header"><span>{attr}</span><span class="guna-score {text_class}">{final} / {max_pts}</span></div><div class="guna-reason">{reason}</div></div>""", unsafe_allow_html=True)
            
        with st.expander("📊 Detailed Transparency Table (Raw vs Final)"):
            df = pd.DataFrame(res['bd'], columns=["Attribute", "Raw Score", "Final Score", "Max", "Logic"])
            totals = pd.DataFrame([["TOTAL", df["Raw Score"].sum(), df["Final Score"].sum(), 36, "-"]], columns=df.columns)
            st.table(pd.concat([df, totals], ignore_index=True))
            
        if res['logs']:
            with st.expander("📜 Ancient Wisdom & Cancellations (Dosha Bhanga)"):
                st.table(pd.DataFrame(res['logs']))
        
        with st.expander("🪐 Mars & Dosha Analysis"):
            st.write(f"**Rajju:** {res['rajju']} (Body Check)"); st.write(f"**Vedha:** {res['vedha']} (Enemy Check)")
            # Fix Display Tuple Bug
            bm = res['b_mars'][1] if isinstance(res['b_mars'], tuple) else res['b_mars']
            gm = res['g_mars'][1] if isinstance(res['g_mars'], tuple) else res['g_mars']
            st.write(f"**Boy Mars:** {bm}"); st.write(f"**Girl Mars:** {gm}")

# --- OTHER TABS ---
with tabs[1]:
    st.header("🔍 Match Finder"); st.caption("Find the best compatible stars for you.")
    col_f1, col_f2 = st.columns(2)
    with col_f1: finder_gender = st.selectbox("I am a", ["Boy", "Girl"]); finder_star = st.selectbox("My Star", NAKSHATRAS)
    with col_f2: finder_rashi_opts = [RASHIS[i] for i in NAK_TO_RASHI_MAP[NAKSHATRAS.index(finder_star)]]; finder_rashi = st.selectbox("My Rashi", finder_rashi_opts)
    if st.button("Find Best Matches", type="primary"):
        with st.spinner("Scanning..."):
            matches = find_best_matches(finder_gender, NAKSHATRAS.index(finder_star), RASHIS.index(finder_rashi))
            st.success(f"Found {len(matches)} combinations!"); st.markdown("### Top Matches")
            if matches:
                top_match = matches[0]
                share_txt = f"I matched my star ({finder_star}) and found the best match is {top_match['Star']} ({top_match['Rashi']}) with a score of {top_match['Final Score']}/36!"
                st.code(share_txt, language="text"); st.caption("👆 Copy top result for WhatsApp")
            df_m = pd.DataFrame(matches); df_m['Rating'] = df_m['Final Score'].apply(lambda x: "⭐⭐⭐" if x > 25 else ("⭐⭐" if x > 18 else "⭐"))
            st.dataframe(df_m, use_container_width=True, hide_index=True)

with tabs[2]:
    st.header("💍 Wedding Dates"); t_rashi = st.selectbox("Select Moon Sign (Rashi)", RASHIS, key="t_r")
    if st.button("Check Auspicious Dates"):
        r_idx = RASHIS.index(t_rashi); st.subheader("Lucky Years")
        for y, s in predict_marriage_luck_years(r_idx): st.write(f"**{y}:** {s}")
        st.subheader("Lucky Month"); st.info(f"❤️ **{predict_wedding_month(r_idx)}**")

with tabs[3]:
    st.header("🤖 Guru AI"); 
    # Use session state for API key so it persists across tabs
    user_key = st.text_input("API Key (aistudio.google.com)", type="password", value=st.session_state.api_key)
    if user_key: st.session_state.api_key = user_key
    
    # CLEAR BUTTON
    if st.button("🗑️ Clear Chat History"):
        st.session_state.messages = []
        st.rerun()
        
    context = "You are a Vedic Astrologer."
    # DYNAMIC SUGGESTIONS
    suggestions = ["What are the 8 Kootas?", "Meaning of Nadi Dosha?", "Best wedding colors?"]
    
    if st.session_state.calculated: 
        r = st.session_state.results
        st.success(f"🧠 **Context Loaded:** {r['b_n']} ❤️ {r['g_n']} (Score: {r['score']})")
        context += f" Match Context: Boy {r['b_n']}, Girl {r['g_n']}. Score: {r['score']}."
        if r.get('b_planets') and r.get('g_planets'):
            b_txt = format_chart_for_ai(r['b_planets']); g_txt = format_chart_for_ai(r['g_planets'])
            context += f" Boy Chart: {b_txt}. Girl Chart: {g_txt}."
        suggestions = ["Analyze this match", "Remedies?", "Is this good for marriage?"]

    cols = st.columns(3); clicked = None
    for i, s in enumerate(suggestions): 
        if cols[i%3].button(s, use_container_width=True): clicked = s
    if st.session_state.api_key:
        for m in st.session_state.messages: st.chat_message(m["role"]).write(m["content"])
        if (prompt := st.chat_input("Ask about stars...")) or clicked:
            final_prompt = prompt if prompt else clicked
            st.session_state.messages.append({"role": "user", "content": final_prompt}); st.chat_message("user").write(final_prompt)
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    ans = handle_ai_query(final_prompt, context, st.session_state.api_key)
                    st.write(ans); st.session_state.messages.append({"role": "assistant", "content": ans})

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
