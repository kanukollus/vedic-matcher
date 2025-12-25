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

# --- TRANSIT DATA (Approximate Solar Months) ---
# Maps Rashi Index (0=Aries) to Date Range
SUN_TRANSIT_DATES = {
    0: "Apr 14 - May 14",   # Sun in Aries
    1: "May 15 - Jun 14",   # Sun in Taurus
    2: "Jun 15 - Jul 15",   # Sun in Gemini
    3: "Jul 16 - Aug 16",   # Sun in Cancer
    4: "Aug 17 - Sep 16",   # Sun in Leo
    5: "Sep 17 - Oct 16",   # Sun in Virgo
    6: "Oct 17 - Nov 15",   # Sun in Libra
    7: "Nov 16 - Dec 15",   # Sun in Scorpio
    8: "Dec 16 - Jan 13",   # Sun in Sagittarius
    9: "Jan 14 - Feb 12",   # Sun in Capricorn
    10: "Feb 13 - Mar 13",  # Sun in Aquarius
    11: "Mar 14 - Apr 13"   # Sun in Pisces
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
    return Nominatim(user_agent="vedic_streamlit_app_v10", timeout=10)

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

# --- PREDICTION LOGIC ---
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

def predict_lucky_months(rashi_idx):
    lucky_houses = [5, 7, 9, 11]
    months = []
    for h in lucky_houses:
        target_rashi = (rashi_idx + h - 1) % 12
        date_range = SUN_TRANSIT_DATES[target_rashi]
        reason = ""
        if h == 5: reason = "❤️ Romance & Love"
        elif h == 7: reason = "💍 Partnership Focus"
        elif h == 9: reason = "🍀 Luck & Blessings"
        elif h == 11: reason = "💰 Gains & Fulfillment"
        months.append((date_range, reason))
    return months

def calculate_all(b_nak, b_rashi, g_nak, g_rashi):
    score = 0
    breakdown = []
    
    # Calculations
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
    
    # Safety Checks
    rajju_group = [0, 1, 2, 3, 4, 3, 2, 1, 0] * 3
    vedha_pairs = {0: 17, 1: 16, 2: 15, 3: 14, 4: 22, 5: 21, 6: 20, 7: 19, 8: 18, 9: 26, 10: 25, 11: 24, 12: 23, 13: 13}
    for k, v in list(vedha_pairs.items()): vedha_pairs[v] = k

    rajju_status = "Pass"
    if rajju_group[b_nak] == rajju_group[g_nak]:
        if maitri >= 4 or b_rashi == g_rashi:
             rajju_status = "Cancelled"
        else:
             rajju_status = "Fail"

    vedha_status = "Pass"
    if vedha_pairs.get(g_nak) == b_nak:
        vedha_status = "Fail"
    
    return score, breakdown, rajju_status, vedha_status

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
        b_city = st.text_input("Boy City", "Hyderabad")
        b_country = st.text_input("Boy Country", "India")
        b_tz = st.number_input("Boy Backup TZ", 5.5)
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
        b_idx = NAKSHATRAS.index(b_star)
        b_poss = NAK_TO_RASHI_MAP[b_idx]
        b_opts = [RASHIS[i] for i in b_poss]
        b_rashi_sel = st.selectbox("Boy Rashi", b_opts)
    with c2:
        st.subheader("Girl Details")
        g_star = st.selectbox("Girl Star", NAKSHATRAS, index=11)
        g_idx = NAKSHATRAS.index(g_star)
        g_poss = NAK_TO_RASHI_MAP[g_idx]
        g_opts = [RASHIS[i] for i in g_poss]
        kanya_default = 0
        if "Virgo (Kanya)" in g_opts:
            kanya_default = g_opts.index("Virgo (Kanya)")
        g_rashi_sel = st.selectbox("Girl Rashi", g_opts, index=kanya_default)

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

        score, breakdown, rajju_status, vedha_status = calculate_all(b_nak, b_rashi, g_nak, g_rashi)
        
        st.divider()
        col1, col2 = st.columns(2)
        col1.info(f"**Boy:** {NAKSHATRAS[b_nak]} | {RASHIS[b_rashi]}")
        col2.info(f"**Girl:** {NAKSHATRAS[g_nak]} | {RASHIS[g_rashi]}")
        
        st.subheader(f"Score: {score} / 36")
        st.progress(score/36)
        
        critical_fail = False
        if rajju_status == "Fail" or vedha_status == "Fail":
            st.error("⚠️ **Compatibility Alignment Check Required**")
            st.info("""
            **Consultation Recommended:** The compatibility tool has identified a few incompatibilities.
            
            This does not strictly mean "No". 
            It is highly recommended to consult a professional astrologer who can look at the **entire birth chart** (including Lagna, 7th House, and planetary positions) to see if there are specific cancellations or other strengths that neutralize this effect.
            """)
            critical_fail = True
        elif rajju_status == "Cancelled":
            st.warning("⚠️ Incompatibilities Detected but Likely Neutralized (Planetary Friendship).")
            
        if not critical_fail:
            if score >= 25:
                st.success("✅ EXCELLENT MATCH (Highly Recommended)")
            elif score >= 18:
                st.success("✅ GOOD MATCH (Proceed)")
            else:
                st.warning("⚠️ NOT RECOMMENDED (Score too low)")
        
        with st.expander("See Detailed Breakdown"):
            df = pd.DataFrame(breakdown, columns=["Koota", "Points", "Max"])
            st.table(df)

        # --- PREDICTIVE TIMING ---
        st.divider()
        with st.expander("🔮 Bonus: Marriage Timing & Lucky Months"):
            st.markdown("### 1. Favorable Years (Jupiter Transit)")
            st.markdown("Jupiter's position for the next 3 years. Lucky houses: 2, 5, 7, 9, 11.")
            st.caption("")
            
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Boy's Lucky Years:**")
                b_years = predict_marriage_luck_years(b_rashi)
                for year, result, desc in b_years:
                    color = "green" if "Excellent" in result else "grey"
                    st.markdown(f"- **{year}:** :{color}[{result}]")
            with c2:
                st.markdown("**Girl's Lucky Years:**")
                g_years = predict_marriage_luck_years(g_rashi)
                for year, result, desc in g_years:
                    color = "green" if "Excellent" in result else "grey"
                    st.markdown(f"- **{year}:** :{color}[{result}]")

            st.markdown("---")
            st.markdown("### 2. Best Months (Sun Transit)")
            st.caption("These are the windows every year where the Sun activates your relationship or luck sectors.")
            
            mc1, mc2 = st.columns(2)
            with mc1:
                st.markdown("**Boy's Lucky Months:**")
                b_months = predict_lucky_months(b_rashi)
                for date_rng, reason in b_months:
                    st.markdown(f"- **{date_rng}:** {reason}")
            with mc2:
                st.markdown("**Girl's Lucky Months:**")
                g_months = predict_lucky_months(g_rashi)
                for date_rng, reason in g_months:
                    st.markdown(f"- **{date_rng}:** {reason}")
            
    except Exception as e:
        st.error(f"An error occurred: {e}")

# --- HOW IT WORKS & DISCLAIMER ---
st.divider()
with st.expander("ℹ️ How this App Works"):
    st.markdown("""
    This app uses a smart **Hybrid Logic** combining the best of both traditions:

    1.  **First, it acts like a South Indian Astrologer (The Safety Check):**
        * It checks for specific star alignments called **Rajju** (Body Compatibility).
        * Imagine the stars mapped to a human body. Traditionally, if both partners belong to the same body part (e.g., both are "Head"), it creates an energetic imbalance.
        * 
        * If an incompatibility is found, the app advises professional consultation to check for exceptions.
        
    2.  **Then, it acts like a North Indian Astrologer (The Scoring):**
        * If the safety checks pass, it calculates the **36 Gunas (Ashta Koota)**.
        * This scores compatibility across 8 areas, ranging from spiritual (Varna) to biological (Nadi).
        * 
        * **Final Score:**
            * **25+:** Excellent
            * **18-24:** Good
            * **Below 18:** Not Recommended
    """)

with st.expander("⚖️ Disclaimer"):
    st.caption("""
    **For Informational Purposes Only.** This application calculates compatibility based on standard astrological algorithms (Lahiri Ayanamsa). 
    **Important:** This app cannot check 7th/8th House strength (Mangal Dosha) as that requires exact birth time to calculate the Ascendant (Lagna). 
    Astrology is a complex field. A computer program cannot replace the intuition and detailed analysis of a qualified human astrologer. 
    Do not make major life decisions solely based on this tool.
    """)
