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
from fpdf import FPDF
from io import BytesIO

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="Vedic Matcher Pro", page_icon="🕉️", layout="wide")

# --- 2. CSS STYLING (UPDATED TO HIDE TOOLBAR) ---
st.markdown("""
<style>
    /* HIDE STREAMLIT UI ELEMENTS */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display:none;}
    
    /* APP STYLING */
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
    
    /* CHART STYLING */
    .chart-container { 
        display: grid; 
        grid-template-columns: repeat(4, 1fr); 
        grid-template-rows: repeat(4, 60px); 
        gap: 2px; 
        background-color: #444; 
        border: 2px solid #333; 
        width: 100%; 
        max-width: 300px; 
        margin: 0 auto; 
        font-size: 10px; 
    }
    .chart-box { background-color: #fffbe6; color: #000; display: flex; align-items: center; justify-content: center; text-align: center; font-weight: bold; padding: 2px; border: 1px solid #ccc; }
    .chart-center { grid-column: 2 / 4; grid-row: 2 / 4; background-color: #fff; display: flex; flex-direction: column; align-items: center; justify-content: center; font-size: 14px; color: #555; }
    
    .verdict-box { background-color: #e8f5e9; border: 1px solid #c8e6c9; padding: 20px; border-radius: 10px; margin-top: 20px; color: #1b5e20; text-align: center; }
    .verdict-title { font-size: 20px; font-weight: bold; margin-bottom: 10px; display: flex; align-items: center; justify-content: center; gap: 10px; }
    
    .synergy-box { background-color: #f3e5f5; border: 1px solid #e1bee7; padding: 15px; border-radius: 10px; margin-top: 15px; color: #4a148c; }
    
    /* GAUGE TITLES */
    .gauge-title {
        text-align: center;
        font-size: 18px;
        font-weight: 600;
        margin-bottom: -10px;
        z-index: 10;
        position: relative;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. SESSION STATE ---
if "calculated" not in st.session_state: st.session_state.calculated = False
if "results" not in st.session_state: st.session_state.results = {}
if "messages" not in st.session_state: st.session_state.messages = []
if "input_mode" not in st.session_state: st.session_state.input_mode = "Birth Details"
if "api_key" not in st.session_state: st.session_state.api_key = ""
if "ai_pitch" not in st.session_state: st.session_state.ai_pitch = ""

# --- 4. DATA CONSTANTS ---
NAKSHATRAS = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra","Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni","Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha","Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta","Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"]
RASHIS = ["Aries (Mesha)", "Taurus (Vrishabha)", "Gemini (Mithuna)", "Cancer (Karka)","Leo (Simha)", "Virgo (Kanya)", "Libra (Tula)", "Scorpio (Vrishchika)","Sagittarius (Dhanu)", "Capricorn (Makara)", "Aquarius (Kumbha)", "Pisces (Meena)"]
SOUTH_CHART_MAP = {11: 0, 0: 1, 1: 2, 2: 3, 10: 4, 3: 7, 9: 8, 4: 11, 8: 12, 7: 13, 6: 14, 5: 15}
NAK_TO_RASHI_MAP = {0: [0], 1: [0], 2: [0, 1], 3: [1], 4: [1, 2], 5: [2], 6: [2, 3], 7: [3], 8: [3], 9: [4], 10: [4], 11: [4, 5], 12: [5], 13: [5, 6], 14: [6], 15: [6, 7], 16: [7], 17: [7], 18: [8], 19: [8], 20: [8, 9], 21: [9], 22: [9, 10], 23: [10], 24: [10, 11], 25: [11], 26: [11]}
MAITRI_TABLE = [[5, 5, 5, 4, 5, 0, 0], [5, 5, 4, 1, 4, 1, 1], [5, 4, 5, 0.5, 5, 3, 0.5],[4, 1, 0.5, 5, 0.5, 5, 4], [5, 4, 5, 0.5, 5, 0.5, 3], [0, 1, 3, 5, 0.5, 5, 5], [0, 1, 0.5, 4, 3, 5, 5]]
GANA_TYPE = [0, 1, 2, 1, 0, 1, 0, 0, 2, 2, 1, 1, 0, 2, 0, 2, 0, 2, 2, 1, 1, 0, 2, 2, 1, 1, 0]
GANA_NAMES = ["Deva (Divine)", "Manushya (Human)", "Rakshasa (Demon)"]
NADI_TYPE = [0, 1, 2, 2, 1, 0, 0, 1, 2, 2, 1, 0, 0, 1, 2, 2, 1, 0, 0, 1, 2, 2, 1, 0, 0, 1, 2]
NADI_NAMES = ["Adi (Start)", "Madhya (Middle)", "Antya (End)"]
SAME_NAKSHATRA_ALLOWED = ["Rohini", "Ardra", "Pushya", "Magha", "Vishakha", "Shravana", "Uttara Bhadrapada", "Revati"]
VARNA_GROUP = [0, 1, 2, 0, 1, 2, 2, 0, 1, 2, 2, 0]
VASHYA_GROUP = [0, 0, 1, 2, 1, 1, 1, 3, 1, 2, 1, 2]
YONI_ID = [0, 1, 2, 3, 3, 4, 5, 2, 5, 6, 6, 7, 8, 9, 8, 9, 10, 10, 4, 11, 12, 11, 13, 0, 13, 7, 1]
YONI_Enemy_Map = {0:8, 1:13, 2:11, 3:12, 4:10, 5:6, 6:5, 7:9, 8:0, 9:7, 10:4, 11:2, 12:3, 13:1}
RASHI_LORDS = [2, 5, 3, 1, 0, 3, 5, 2, 4, 6, 6, 4] 
# 0:Sun, 1:Moon, 2:Mars, 3:Merc, 4:Jup, 5:Ven, 6:Sat
PLANET_NAMES_MAP = {0: "Sun", 1: "Moon", 2: "Mars", 3: "Mercury", 4: "Jupiter", 5: "Venus", 6: "Saturn"}

DASHA_ORDER = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
DASHA_YEARS = {"Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7, "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17}
SPECIAL_ASPECTS = {"Mars": [4, 7, 8], "Jupiter": [5, 7, 9], "Saturn": [3, 7, 10], "Rahu": [5, 7, 9], "Ketu": [5, 7, 9]}
SUN_TRANSIT_DATES = {0: "Apr 14 - May 14", 1: "May 15 - Jun 14", 2: "Jun 15 - Jul 15", 3: "Jul 16 - Aug 16", 4: "Aug 17 - Sep 16", 5: "Sep 17 - Oct 16", 6: "Oct 17 - Nov 15", 7: "Nov 16 - Dec 15", 8: "Dec 16 - Jan 13", 9: "Jan 14 - Feb 12", 10: "Feb 13 - Mar 13", 11: "Mar 14 - Apr 13"}
NAK_TRAITS = {0: {"Trait": "Pioneer"}, 1: {"Trait": "Creative"}, 2: {"Trait": "Sharp"}, 3: {"Trait": "Sensual"}, 4: {"Trait": "Curious"}, 5: {"Trait": "Intellectual"}, 6: {"Trait": "Nurturing"}, 7: {"Trait": "Spiritual"}, 8: {"Trait": "Mystical"}, 9: {"Trait": "Royal"}, 10: {"Trait": "Social"}, 11: {"Trait": "Charitable"}, 12: {"Trait": "Skilled"}, 13: {"Trait": "Beautiful"}, 14: {"Trait": "Independent"}, 15: {"Trait": "Focused"}, 16: {"Trait": "Friendship"}, 17: {"Trait": "Protective"}, 18: {"Trait": "Deep"}, 19: {"Trait": "Invincible"}, 20: {"Trait": "Victory"}, 21: {"Trait": "Listener"}, 22: {"Trait": "Musical"}, 23: {"Trait": "Healer"}, 24: {"Trait": "Passionate"}, 25: {"Trait": "Ascetic"}, 26: {"Trait": "Complete"}}
SYNERGY_MEANINGS = {
    "Sun": "Aligned Egos. You shine in similar ways and understand each other's pride.",
    "Moon": "Deep Empathy. You intuitively understand each other's moods and needs.",
    "Mars": "Synced Energy. You share the same drive, passion, and fighting style.",
    "Merc": "Intellectual Bond. You communicate effortlessly and think alike.",
    "Jupiter": "Shared Values. You have the same moral compass and life philosophy.",
    "Venus": "Romantic Sync. You share similar tastes in love, luxury, and aesthetics.",
    "Saturn": "Karmic Strength. You share a similar work ethic and approach to challenges.",
    "Rahu": "Destiny Link. A magnetic, obsessive pull towards similar unconventional paths.",
    "Ketu": "Past Life Bond. A deep, spiritual sense of knowing each other from before."
}

# --- 5. HELPER FUNCTIONS ---

import re

def clean_text(text):
    if not isinstance(text, str): 
        return str(text)
    
    # Step 1: Manual mapping of common symbols to safe text
    replacements = {
        "✅": "[PASS]", "❌": "[FAIL]", "⚠️": "[WARN]", 
        "✨": "*", "⭐": "*", "🔥": "[VIGOR]", 
        "🛡️": "[SHIELD]", "🤖": "AI:", "🕉️": "OM"
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
        
    # Step 2: The "Burn-It-Down" Safety Net
    # This encodes to ASCII and ignores/deletes anything it doesn't recognize.
    # It effectively removes \u2728 and any other offending characters.
    return text.encode('ascii', 'ignore').decode('ascii')

def format_chart_for_ai(chart_data):
    if not chart_data: return "Chart not generated."
    readable = []
    for r_idx, planets in chart_data.items():
        if planets: readable.append(f"{RASHIS[r_idx]}: {', '.join(planets)}")
    return "; ".join(readable)

def get_shared_positions(b_chart, g_chart):
    shared = []
    if not b_chart or not g_chart: return []
    b_pos = {}
    g_pos = {}
    for r_idx, planets in b_chart.items():
        for p in planets: b_pos[p] = r_idx
    for r_idx, planets in g_chart.items():
        for p in planets: g_pos[p] = r_idx
        
    for p in b_pos:
        if p in g_pos and b_pos[p] == g_pos[p]:
            r_name = RASHIS[b_pos[p]].split(" ")[0] 
            p_key = "Mars" if p == "Ma" else ("Jupiter" if p == "Ju" else ("Saturn" if p == "Sa" else ("Rahu" if p == "Ra" else ("Ketu" if p == "Ke" else ("Sun" if p == "Su" else ("Moon" if p == "Mo" else ("Mercury" if p == "Me" else ("Venus" if p == "Ve" else p))))))))
            meaning = SYNERGY_MEANINGS.get(p_key, "Strong Connection")
            shared.append(f"**Shared {p_key} ({r_name}):** {meaning}")
    return shared

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

def to_csv(df):
    output = BytesIO()
    df.to_csv(output, index=False)
    return output.getvalue()

# --- PDF GENERATOR ---
# --- 5. UPDATED PROFESSIONAL PDF GENERATOR (FPDF) ---
class PDFReport(FPDF):
    def header(self):
        # Professional Header with Gold Theme
        self.set_fill_color(255, 215, 0) # Gold
        self.rect(0, 0, 210, 15, 'F')
        self.set_font('Arial', 'B', 12)
        self.set_text_color(0, 0, 0)
        self.cell(0, 10, 'OFFICIAL VEDIC COMPATIBILITY REPORT - 2026 Edition', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Page {self.page_no()} | Generated by Vedic Matcher Pro AI | (c) 2026', 0, 0, 'C')

    def chapter_title(self, title, color=(0, 51, 102)):
        self.set_font('Arial', 'B', 14)
        self.set_text_color(*color)
        self.cell(0, 10, title.upper(), 'B', 1, 'L')
        self.ln(4)

    def chapter_body(self, body):
        self.set_font('Arial', '', 10)
        self.set_text_color(50, 50, 50)
        self.multi_cell(0, 6, body)
        self.ln()

    def koota_row(self, attr, score, max_pts, logic, area):
        # Store current Y to draw shapes
        current_y = self.get_y()
        
        # 1. Draw the Attribute & Area
        self.set_text_color(50, 50, 50)
        self.cell(40, 8, clean_text(attr), 1)
        self.cell(35, 8, clean_text(area), 1)
        
        # 2. Draw the Score with a Background Color (The Visual Indicator)
        percent = (score / max_pts) if max_pts > 0 else 0
        if percent >= 0.8: self.set_fill_color(200, 255, 200) # Light Green
        elif percent >= 0.5: self.set_fill_color(255, 240, 200) # Light Gold
        else: self.set_fill_color(255, 200, 200) # Light Red
        
        self.cell(20, 8, f"{score}/{max_pts}", 1, 0, 'C', 1)
        
        # 3. Draw the Logic (Cleaned of Emojis)
        self.set_text_color(50, 50, 50)
        # Truncate logic to prevent overflow
        safe_logic = clean_text(logic)
        if len(safe_logic) > 55: safe_logic = safe_logic[:52] + "..."
        self.cell(95, 8, safe_logic, 1)
        self.ln()

def generate_pdf(res):
    pdf = PDFReport()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # 1. SUMMARY SCORECARD (The "Certificate" Page)
    pdf.set_font('Arial', 'B', 24)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 20, "MATCH SUMMARY", 0, 1, 'C')
    
    # Verdict Box
    score_val = res['score']
    status = "EXCELLENT" if score_val > 24 else ("GOOD" if score_val > 18 else "NOT RECOMMENDED")
    color = (0, 128, 0) if score_val > 24 else ((255, 140, 0) if score_val > 18 else (200, 0, 0))
    
    pdf.set_draw_color(*color)
    pdf.set_line_width(1)
    pdf.rect(45, 45, 120, 40)
    pdf.set_xy(45, 50)
    pdf.set_font('Arial', 'B', 16)
    pdf.set_text_color(*color)
    pdf.cell(120, 10, f"{status} MATCH", 0, 1, 'C')
    pdf.set_font('Arial', 'B', 32)
    pdf.set_xy(45, 65)
    pdf.cell(120, 15, f"{score_val} / 36", 0, 1, 'C')
    
    pdf.set_xy(10, 95)
    pdf.chapter_title("1. Birth Constellations")
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(95, 10, f"GROOM: {res.get('b_info')}", 1, 0, 'C')
    pdf.cell(95, 10, f"BRIDE: {res.get('g_info')}", 1, 1, 'C')
    pdf.ln(5)

    # 2. GURU AI - KARMIC INSIGHTS (Dynamic & Crash-Proof)
    if st.session_state.ai_pitch:
        # Step 1: Sanitize the text immediately using the force-filter
        cleaned_pitch = clean_text(st.session_state.ai_pitch)
        
        # Step 2: Calculate how many lines this text will occupy
        line_height = 6
        text_width = 180
        # split_only=True is a professional FPDF feature to pre-calculate height
        lines = pdf.multi_cell(text_width, line_height, cleaned_pitch, split_only=True)
        box_height = (len(lines) * line_height) + 18 # 18 units for title & padding

        # Step 3: Draw the professional shaded background box
        pdf.set_fill_color(245, 245, 255) # Light Lavender
        pdf.rect(10, pdf.get_y(), 190, box_height, 'F')
        
        # Step 4: Render Content
        pdf.chapter_title("2. Guru AI - Karmic Insight")
        pdf.set_font('Arial', 'I', 10)
        pdf.set_text_color(40, 40, 80) # High-contrast navy blue
        
        pdf.set_x(15) # Internal padding
        pdf.multi_cell(text_width, line_height, cleaned_pitch)
        
        # Reset colors and add spacing for the next section
        pdf.set_text_color(0, 0, 0)
        pdf.ln(10)
    
    
    # 3. ASHTA KOOTA ANALYSIS (Professional Table)
    pdf.chapter_title("3. Detailed Guna Analysis")
    pdf.set_font('Arial', 'B', 10)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(40, 8, "Attribute", 1, 0, 'L', 1)
    pdf.cell(35, 8, "Life Area", 1, 0, 'L', 1)
    pdf.cell(20, 8, "Score", 1, 0, 'C', 1)
    pdf.cell(95, 8, "Logic / Remedial Fix", 1, 1, 'L', 1)
    
    area_map = {
        "Varna": "Work/Ego", "Vashya": "Dominance", "Tara": "Destiny",
        "Yoni": "Intimacy", "Maitri": "Friendship", "Gana": "Temperament",
        "Bhakoot": "Love/Wealth", "Nadi": "Genetics"
    }
    
    for item in res['bd']:
        attr, raw, final, mx, reason = item
        fix_txt = reason
        for log in res['logs']:
            if log['Attribute'] == attr: fix_txt = f"Fixed: {log['Fix']}"
        pdf.koota_row(attr, final, mx, fix_txt, area_map.get(attr, "General"))

    # 4. DOSHA & MARS (The Safety Check)
    pdf.add_page()
    pdf.chapter_title("4. Critical Dosha & Mars (Mangal) Analysis")
    bm = res['b_mars'][1] if isinstance(res['b_mars'], tuple) else res['b_mars']
    gm = res['g_mars'][1] if isinstance(res['g_mars'], tuple) else res['g_mars']
    
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(40, 10, "RAJJU DOSHA:", 0); pdf.set_font('Arial', '', 10); pdf.cell(0, 10, clean_text(res['rajju']), 0, 1)
    pdf.set_font('Arial', 'B', 10); pdf.cell(40, 10, "VEDHA DOSHA:", 0); pdf.set_font('Arial', '', 10); pdf.cell(0, 10, clean_text(res['vedha']), 0, 1)
    pdf.ln(2)
    pdf.chapter_body(f"Groom Mars Status: {bm}\nBride Mars Status: {gm}")

    # 5. PLANETARY POSITIONS (Structured Table)
    if res.get('b_planets'):
        pdf.chapter_title("5. Planetary Summary")
        pdf.set_font('Arial', 'B', 9)
        pdf.cell(95, 7, "Groom (D1 Chart)", 1, 0, 'C', 1)
        pdf.cell(95, 7, "Bride (D1 Chart)", 1, 1, 'C', 1)
        pdf.set_font('Arial', '', 8)
        
        # Zip planetary data for side-by-side view
        b_data = [f"{RASHIS[r].split(' ')[0]}: {', '.join(p)}" for r, p in res['b_planets'].items()]
        g_data = [f"{RASHIS[r].split(' ')[0]}: {', '.join(p)}" for r, p in res['g_planets'].items()]
        for i in range(max(len(b_data), len(g_data))):
            b_val = b_data[i] if i < len(b_data) else ""
            g_val = g_data[i] if i < len(g_data) else ""
            pdf.cell(95, 6, clean_text(b_val), 1)
            pdf.cell(95, 6, clean_text(g_val), 1)
            pdf.ln()

    # 6. DISCLAIMER
    pdf.ln(10)
    pdf.set_font('Arial', 'I', 7)
    pdf.multi_cell(0, 4, "DISCLAIMER: This 2026 AI-enhanced report is for guidance based on Vedic scripts. Astrological results depend on multiple factors; marriage decisions should involve mutual understanding and personal consultation with a qualified professional.")

    return pdf.output(dest='S').encode('latin-1', 'replace')
    
@st.cache_resource
def get_geolocator(): return Nominatim(user_agent="vedic_matcher_v112_final_defaults", timeout=10)
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

def calculate_d9_position(longitude):
    d1_rashi = int(longitude / 30)
    rem_deg = longitude % 30
    nav_num = int(rem_deg / 3.33333333333)
    if d1_rashi in [0, 4, 8]: start_sign = 0 
    elif d1_rashi in [1, 5, 9]: start_sign = 9 
    elif d1_rashi in [2, 6, 10]: start_sign = 6 
    elif d1_rashi in [3, 7, 11]: start_sign = 3 
    return (start_sign + nav_num) % 12

def calculate_rahu_ketu_mean(jd):
    t = (jd - 2451545.0) / 36525.0
    omega = 125.04452 - 1934.136261 * t + 0.0020708 * t * t + t * t * t / 450000.0
    rahu_long = omega % 360
    ketu_long = (rahu_long + 180) % 360
    return rahu_long, ketu_long

def calculate_ascendant(observer, jd):
    lst_rad = float(observer.sidereal_time()) 
    lat_rad = float(observer.lat)
    eps_rad = math.radians(23.4392911)
    y = math.cos(lst_rad)
    x = - (math.sin(lst_rad) * math.cos(eps_rad) + math.tan(lat_rad) * math.sin(eps_rad))
    asc_rad = math.atan2(y, x)
    asc_deg = math.degrees(asc_rad)
    return asc_deg % 360

def get_d9_rashi_from_pada(nak_idx, pada):
    total_padas = (nak_idx * 4) + (pada - 1)
    return total_padas % 12

def get_nak_rashi_pada(long):
    nak_idx = int(long / 13.33333333333)
    rashi_idx = int(long / 30)
    deg_in_nak = long % 13.33333333333
    pada = int(deg_in_nak / 3.33333333333) + 1
    return nak_idx, rashi_idx, pada

def get_planetary_positions(date_obj, time_obj, city, country, detailed=False):
    dt = datetime.datetime.combine(date_obj, time_obj)
    offset, msg = get_offset_smart(city, country, dt, 5.5)
    obs = ephem.Observer(); obs.date = dt - datetime.timedelta(hours=offset)
    obs.lat, obs.lon = '28.6139', '77.2090' 
    if city: 
        loc = get_cached_coords(city, country)
        if loc: obs.lat, obs.lon = str(loc.latitude), str(loc.longitude)
    
    # Base bodies
    moon = ephem.Moon(); moon.compute(obs)
    mars = ephem.Mars(); mars.compute(obs)
    sun = ephem.Sun(); sun.compute(obs)
    
    # Ayanamsa Calculation (Lahiri)
    # t = (jd - 2451545.0) / 36525
    jd = ephem.julian_date(obs.date)
    t = (jd - 2451545.0) / 36525.0
    ayanamsa = 23.85 + 1.4 * t # Simplified rate
    
    s_moon = (math.degrees(ephem.Ecliptic(moon).lon) - ayanamsa) % 360
    s_mars = (math.degrees(ephem.Ecliptic(mars).lon) - ayanamsa) % 360
    s_sun = (math.degrees(ephem.Ecliptic(sun).lon) - ayanamsa) % 360
    
    d1_chart_data = None
    d9_chart_data = None
    
    if detailed:
        bodies = [ephem.Sun(), ephem.Moon(), ephem.Mars(), ephem.Mercury(), ephem.Jupiter(), ephem.Venus(), ephem.Saturn()]
        names = ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa"] 
        d1_chart_data = {}; d9_chart_data = {}
        for body, name in zip(bodies, names):
            body.compute(obs)
            long = (math.degrees(ephem.Ecliptic(body).lon) - ayanamsa) % 360
            r_idx_d1 = int(long / 30)
            if r_idx_d1 not in d1_chart_data: d1_chart_data[r_idx_d1] = []
            d1_chart_data[r_idx_d1].append(name)
            r_idx_d9 = calculate_d9_position(long)
            if r_idx_d9 not in d9_chart_data: d9_chart_data[r_idx_d9] = []
            d9_chart_data[r_idx_d9].append(name)
            
        rahu_l, ketu_l = calculate_rahu_ketu_mean(jd)
        rahu_sid = (rahu_l - ayanamsa) % 360; ketu_sid = (ketu_l - ayanamsa) % 360
        r_idx = int(rahu_sid / 30)
        if r_idx not in d1_chart_data: d1_chart_data[r_idx] = []
        d1_chart_data[r_idx].append("Ra")
        r_d9 = calculate_d9_position(rahu_sid)
        if r_d9 not in d9_chart_data: d9_chart_data[r_d9] = []
        d9_chart_data[r_d9].append("Ra")
        k_idx = int(ketu_sid / 30)
        if k_idx not in d1_chart_data: d1_chart_data[k_idx] = []
        d1_chart_data[k_idx].append("Ke")
        k_d9 = calculate_d9_position(ketu_sid)
        if k_d9 not in d9_chart_data: d9_chart_data[k_d9] = []
        d9_chart_data[k_d9].append("Ke")
        
        asc_trop = calculate_ascendant(obs, jd)
        asc_sid = (asc_trop - ayanamsa) % 360
        a_idx = int(asc_sid / 30)
        if a_idx not in d1_chart_data: d1_chart_data[a_idx] = []
        d1_chart_data[a_idx].append("Asc")
        a_d9 = calculate_d9_position(asc_sid)
        if a_d9 not in d9_chart_data: d9_chart_data[a_d9] = []
        d9_chart_data[a_d9].append("Asc")

    return s_moon, s_mars, s_sun, msg, d1_chart_data, d9_chart_data

def check_mars_dosha_smart(moon_rashi, mars_long):
    mars_rashi = int(mars_long / 30)
    house_diff = (mars_rashi - moon_rashi) % 12 + 1
    if house_diff in [2, 4, 7, 8, 12]:
        if mars_rashi == 0 or mars_rashi == 7: return False, f"✅ Balanced (Mars in Own Sign - House {house_diff})"
        elif mars_rashi == 9: return False, f"✅ Balanced (Mars Exalted - House {house_diff})"
        return True, f"🔥 **High Intensity (House {house_diff}):** Mars influences {('Longevity & Intimacy' if house_diff==8 else ('Marriage Partnership' if house_diff==7 else 'Family/Temper'))}. Brings deep passion but requires a strong partner."
    return False, "✨ **Calm:** Mars is placed peacefully. No aggressive energy spikes."

def render_south_indian_chart(positions, title):
    grid_items = [""] * 16
    for rashi_idx, planets in positions.items():
        if rashi_idx in SOUTH_CHART_MAP:
            grid_pos = SOUTH_CHART_MAP[rashi_idx]
            grid_items[grid_pos] = "<br>".join(planets)
    return f"""
    <div style="text-align: center; margin-bottom: 2px; font-size: 12px;"><strong>{title}</strong></div>
    <div class="chart-container">
        <div class="chart-box" style="grid-column: 1; grid-row: 1;">{grid_items[0]}<br><span style='font-size:8px; color:grey'>Pis</span></div>
        <div class="chart-box" style="grid-column: 2; grid-row: 1;">{grid_items[1]}<br><span style='font-size:8px; color:grey'>Ari</span></div>
        <div class="chart-box" style="grid-column: 3; grid-row: 1;">{grid_items[2]}<br><span style='font-size:8px; color:grey'>Tau</span></div>
        <div class="chart-box" style="grid-column: 4; grid-row: 1;">{grid_items[3]}<br><span style='font-size:8px; color:grey'>Gem</span></div>
        <div class="chart-box" style="grid-column: 1; grid-row: 2;">{grid_items[4]}<br><span style='font-size:8px; color:grey'>Aqu</span></div>
        <div class="chart-center" style="font-size: 10px;">{title.split(" ")[0]}</div>
        <div class="chart-box" style="grid-column: 4; grid-row: 2;">{grid_items[7]}<br><span style='font-size:8px; color:grey'>Can</span></div>
        <div class="chart-box" style="grid-column: 1; grid-row: 3;">{grid_items[8]}<br><span style='font-size:8px; color:grey'>Cap</span></div>
        <div class="chart-box" style="grid-column: 4; grid-row: 3;">{grid_items[11]}<br><span style='font-size:8px; color:grey'>Leo</span></div>
        <div class="chart-box" style="grid-column: 1; grid-row: 4;">{grid_items[12]}<br><span style='font-size:8px; color:grey'>Sag</span></div>
        <div class="chart-box" style="grid-column: 2; grid-row: 4;">{grid_items[13]}<br><span style='font-size:8px; color:grey'>Sco</span></div>
        <div class="chart-box" style="grid-column: 3; grid-row: 4;">{grid_items[14]}<br><span style='font-size:8px; color:grey'>Lib</span></div>
        <div class="chart-box" style="grid-column: 4; grid-row: 4;">{grid_items[15]}<br><span style='font-size:8px; color:grey'>Vir</span></div>
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
        if any(p in ["Sa", "Ma", "Ra", "Ke", "Su"] for p in occupants): 
            observations.append(f"⚠️ **{names} in 7th House:** This placement often creates friction or delays in marriage. It requires maturity.")
        elif any(p in ["Ju", "Ve", "Me"] for p in occupants):
            observations.append(f"✅ **{names} in 7th House:** A blessing. These planets bring natural harmony and affection.")
    aspectors = []
    for r_idx, planets in chart_data.items():
        dist = (house_7_idx - r_idx) % 12 + 1 
        for p in planets:
            p_full = "Mars" if p == "Ma" else ("Jupiter" if p == "Ju" else ("Saturn" if p == "Sa" else ("Rahu" if p == "Ra" else ("Ketu" if p == "Ke" else p))))
            if p_full in SPECIAL_ASPECTS and dist in SPECIAL_ASPECTS[p_full]: aspectors.append(p_full)
            elif dist == 7: aspectors.append(p_full)
    if aspectors:
        aspectors = list(set(aspectors))
        if "Saturn" in aspectors: observations.append("ℹ️ **Saturn's Gaze:** Saturn looks at the marriage house. This indicates the relationship will mature slowly.")
        if "Mars" in aspectors: observations.append("🔥 **Mars' Gaze:** Mars adds energy and passion, but arguments can get heated.")
        if "Jupiter" in aspectors: observations.append("🛡️ **Jupiter's Gaze:** The 'Great Benefic' protects the marriage like a safety net.")
    return observations

def generate_human_verdict(score, rajju, b_obs, g_obs, b_dasha, g_dasha):
    verdict = ""
    if score >= 25: verdict += "Mathematically, this is an **Excellent Match**."
    elif score >= 18: verdict += "Mathematically, this is a **Good Match** compatible for marriage."
    else: verdict += "Mathematically, the compatibility score is on the lower side."
    if rajju == "Fail": verdict += " **Rajju Dosha** suggests paying attention to health/physical compatibility."
    elif rajju == "Cancelled": verdict += " Critical Doshas are effectively **cancelled**."
    
    # Handle missing dasha gracefully
    if "Unknown" in b_dasha:
        verdict += "\n\n**Time Cycles:** Skipped (Requires full birth details for Dasha calculation)."
    else:
        verdict += f"\n\n**Time Cycles:** The boy is in a period of *{b_dasha}* and the girl is in *{g_dasha}*. "
        if b_dasha == g_dasha and b_dasha in ["Rahu", "Ketu", "Saturn"]:
            verdict += "Since both are running similar intense periods, mutual patience is key."
        else:
            verdict += "These periods complement each other well for growth."
    
    verdict += "\n\n**Planetary Influence:** "
    if any("Aspect" in o for o in b_obs + g_obs):
        verdict += "Planetary aspects on the marriage house indicate a relationship that will mature beautifully with time."
    elif any("Occupants" in o for o in b_obs + g_obs):
        verdict += "Planets occupying the 7th house add specific flavors (energy or wisdom) to the bond."
    else: verdict += "The planetary positions are largely neutral, leaving the relationship's success in your own hands."
    return verdict

def calculate_all(b_nak, b_rashi, g_nak, g_rashi, b_d9_rashi=None, g_d9_rashi=None):
    maitri_raw = MAITRI_TABLE[RASHI_LORDS[b_rashi]][RASHI_LORDS[g_rashi]]
    friends = maitri_raw >= 4
    d9_friendly = False
    
    b_lord_name = PLANET_NAMES_MAP[RASHI_LORDS[b_rashi]]
    g_lord_name = PLANET_NAMES_MAP[RASHI_LORDS[g_rashi]]
    
    # Navamsa Lord Logic
    if b_d9_rashi is not None and g_d9_rashi is not None:
        d9_lord_b = RASHI_LORDS[b_d9_rashi]
        d9_lord_g = RASHI_LORDS[g_d9_rashi]
        b_d9_name = PLANET_NAMES_MAP[d9_lord_b]
        g_d9_name = PLANET_NAMES_MAP[d9_lord_g]
        
        if MAITRI_TABLE[d9_lord_b][d9_lord_g] >= 4:
            d9_friendly = True
    
    score = 0; bd = []; logs = []
    
    # 1. Varna
    v_raw = 1 if VARNA_GROUP[b_rashi] <= VARNA_GROUP[g_rashi] else 0
    v_final = v_raw; reason = "Natural Match" if v_raw == 1 else "Mismatch"
    fix_msg = None
    if v_raw == 0:
        if friends: fix_msg = "Graha Maitri is Friendly"
        elif d9_friendly: fix_msg = f"Navamsa Lords ({b_d9_name} & {g_d9_name}) are Friendly"
    if fix_msg:
        v_final = 1; reason = "Boosted by Support"
        logs.append({"Attribute": "Varna", "Problem": "Ego Conflict", "Fix": fix_msg, "Source": "Muhurtha Chintamani"})
    score += v_final; bd.append(("Varna", v_raw, v_final, 1, reason))
    
    # 4. Yoni
    y_raw = 4 if YONI_ID[b_nak] == YONI_ID[g_nak] else (0 if YONI_Enemy_Map.get(YONI_ID[b_nak]) == YONI_ID[g_nak] else 2)
    y_final = y_raw 
    
    # 2. Vashya
    va_raw = 0
    if VASHYA_GROUP[b_rashi] == VASHYA_GROUP[g_rashi]: va_raw = 2
    elif (VASHYA_GROUP[b_rashi] == 0 and VASHYA_GROUP[g_rashi] == 1) or (VASHYA_GROUP[b_rashi] == 1 and VASHYA_GROUP[g_rashi] == 0): va_raw = 1 
    elif VASHYA_GROUP[b_rashi] != VASHYA_GROUP[g_rashi]: va_raw = 0.5 
    va_final = va_raw; reason = "Magnetic" if va_raw >= 1 else "Mismatch"
    fix_msg = None
    if va_raw < 2:
        if y_raw == 4: fix_msg = "Yoni is Perfect (4/4)"
        elif friends: fix_msg = "Graha Maitri is Friendly"
        elif d9_friendly: fix_msg = f"Navamsa Lords ({b_d9_name} & {g_d9_name}) are Friendly"
    if fix_msg: 
        va_final = 2; reason = "Boosted by Support"
        logs.append({"Attribute": "Vashya", "Problem": f"Attraction Mismatch", "Fix": fix_msg, "Source": "Brihat Parashara"})
    score += va_final; bd.append(("Vashya", va_raw, va_final, 2, reason))
    
    # 3. Tara
    cnt_b_g = (g_nak - b_nak) % 27 + 1
    cnt_g_b = (b_nak - g_nak) % 27 + 1
    t1_bad = cnt_b_g % 9 in [3, 5, 7]
    t2_bad = cnt_g_b % 9 in [3, 5, 7]
    t_raw = 3
    if t1_bad and t2_bad: t_raw = 0
    elif t1_bad or t2_bad: t_raw = 1.5
    t_final = t_raw; reason = "Benefic" if t_raw == 3 else ("Mixed" if t_raw == 1.5 else "Malefic")
    fix_msg = None
    if t_raw < 3:
        if friends: fix_msg = "Graha Maitri is Friendly"
        elif d9_friendly: fix_msg = f"Navamsa Lords ({b_d9_name} & {g_d9_name}) are Friendly"
    if fix_msg: 
        t_final = 3; reason = "Boosted by Support"
        logs.append({"Attribute": "Tara", "Problem": "Malefic Star Position", "Fix": fix_msg, "Source": "Muhurtha Martanda"})
    score += t_final; bd.append(("Tara", t_raw, t_final, 3, reason))
    
    # 7. Bhakoot
    dist = (b_rashi-g_rashi)%12
    bh_raw = 7 if dist not in [1, 11, 4, 8, 5, 7] else 0
    bh_final = bh_raw; reason = "Love Flow" if bh_raw == 7 else "Blocked"
    fix_msg = None
    if bh_raw == 0:
        if friends: fix_msg = "Graha Maitri is Friendly"
        elif NADI_TYPE[b_nak]!=NADI_TYPE[g_nak]: fix_msg = "Nadi is Different (Healthy)"
    if fix_msg: 
        bh_final = 7; reason = "Compensated"
        logs.append({"Attribute": "Bhakoot", "Problem": f"Bad Position", "Fix": fix_msg, "Source": "Brihat Samhita"})
    
    # 4. Yoni Final
    y_final = y_raw; reason = "Perfect" if y_raw == 4 else "Mismatch"
    fix_msg = None
    if y_raw < 4:
        if friends: fix_msg = "Graha Maitri is Friendly"
        elif d9_friendly: fix_msg = f"Navamsa Lords ({b_d9_name} & {g_d9_name}) are Friendly"
        elif bh_final == 7: fix_msg = "Bhakoot is Beneficial"
        elif va_final >= 1: fix_msg = "Vashya is Magnetic"
    if fix_msg: 
        y_final = 4; reason = "Compensated"
        logs.append({"Attribute": "Yoni", "Problem": "Nature Mismatch", "Fix": fix_msg, "Source": "Jataka Parijata"})
    score += y_final; bd.append(("Yoni", y_raw, y_final, 4, reason))
    
    # 5. Maitri
    m_final = maitri_raw
    fix_msg = None
    if maitri_raw < 5:
        if d9_friendly: fix_msg = f"Navamsa Lords ({b_d9_name} & {g_d9_name}) are Friendly"
        elif bh_final == 7: fix_msg = "Bhakoot is Beneficial"
    if fix_msg:
        m_final = 5; reason = "Restored"
        logs.append({"Attribute": "Maitri", "Problem": "Planetary Enemy", "Fix": fix_msg, "Source": "Brihat Parashara"})
    else:
        reason = "Friendly" if m_final>=4 else "Enemy"
    score += m_final; bd.append(("Maitri", maitri_raw, m_final, 5, reason))
    
    # 6. Gana
    gb, gg = GANA_TYPE[b_nak], GANA_TYPE[g_nak]
    ga_raw = 0
    if gb == gg: ga_raw = 6
    elif (gb==0 and gg==1) or (gb==1 and gg==0): ga_raw = 6
    elif (gb==0 and gg==2) or (gb==2 and gg==0): ga_raw = 1
    elif (gb==1 and gg==2) or (gb==2 and gg==1): ga_raw = 0
    
    # HARDCODED EXCEPTION: Jyeshtha Girl + PB Boy (Aquarius)
    if NAKSHATRAS[g_nak] == "Jyeshtha" and NAKSHATRAS[b_nak] == "Purva Bhadrapada" and RASHIS[b_rashi].startswith("Aquarius"):
        ga_raw = 6 # Force Override Raw Score
    
    ga_final = ga_raw; reason = "Match" if ga_raw >= 5 else "Mismatch"
    star_dist = (g_nak - b_nak) % 27 + 1
    fix_msg = None
    if ga_raw < 6:
        if star_dist >= 14: fix_msg = "Star Distance > 14"
        elif friends: fix_msg = "Graha Maitri is Friendly"
        elif d9_friendly: fix_msg = f"Navamsa Lords ({b_d9_name} & {g_d9_name}) are Friendly"
        elif bh_final == 7: fix_msg = "Bhakoot is Beneficial"
    if fix_msg:
        ga_final = 6; reason = "Boosted"
        logs.append({"Attribute": "Gana", "Problem": "Temperament Clash", "Fix": fix_msg, "Source": "Peeyushadhara"})
    score += ga_final; bd.append(("Gana", ga_raw, ga_final, 6, reason))
    
    # 7. Bhakoot Final
    score += bh_final; bd.append(("Bhakoot", bh_raw, bh_final, 7, "Love Flow" if bh_final == 7 else "Blocked"))
    
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
    rajju_status = "Pass"
    vedha_status = "Pass"
    rajju_group = [0, 1, 2, 3, 4, 3, 2, 1, 0] * 3
    if rajju_group[b_nak] == rajju_group[g_nak]:
        rajju_status = "Fail"
        if friends or b_rashi == g_rashi: 
            rajju_status = "Cancelled"
            logs.append({"Attribute": "Rajju", "Problem": "Body Part Clash", "Fix": "Maitri overrides Rajju.", "Source": "Kala Vidhana"})
    
    vedha_pairs = {0: 17, 1: 16, 2: 15, 3: 14, 4: 22, 5: 21, 6: 20, 7: 19, 8: 18, 9: 26, 10: 25, 11: 24, 12: 23, 13: 13}
    for k, v in list(vedha_pairs.items()): vedha_pairs[v] = k
    if vedha_pairs.get(g_nak) == b_nak:
        vedha_status = "Fail"
    
    # CRITICAL SAFETY CHECK
    bhakoot_score = 0; nadi_score = 0
    for item in bd:
        if item[0] == "Bhakoot": bhakoot_score = item[2]
        if item[0] == "Nadi": nadi_score = item[2]
        
    final_status_override = None
    if score > 18 and bhakoot_score == 0 and nadi_score == 0:
        final_status_override = "Risky Match ❌"

    return score, bd, logs, rajju_status, vedha_status, final_status_override

def find_best_matches(source_gender, s_nak, s_rashi, s_pada):
    matches = []
    s_d9_rashi = get_d9_rashi_from_pada(s_nak, s_pada)
    for i in range(27): 
        target_star_name = NAKSHATRAS[i]
        
        # Iterate all 4 padas
        for t_pada in range(1, 5):
            valid_rashis = NAK_TO_RASHI_MAP[i]
            # Precise Rashi Calculation for Pada
            star_span = 13.3333333333333
            pada_span = 3.3333333333333
            star_start_deg = i * star_span
            pada_start_deg = star_start_deg + (t_pada - 1) * pada_span
            mid_pada_deg = pada_start_deg + 1.0 
            t_rashi_idx = int(mid_pada_deg / 30)
            
            t_d9_rashi = get_d9_rashi_from_pada(i, t_pada)
            
            if source_gender == "Boy": 
                score, bd, logs, _, _, safety = calculate_all(s_nak, s_rashi, i, t_rashi_idx, s_d9_rashi, t_d9_rashi)
            else: 
                score, bd, logs, _, _, safety = calculate_all(i, t_rashi_idx, s_nak, s_rashi, t_d9_rashi, s_d9_rashi)
            
            is_risky = (safety == "Risky Match ❌")
            
            if score > 18:
                raw_score = sum(item[1] for item in bd)
                rashi_simple = RASHIS[t_rashi_idx].split(" ")[0]
                risk_icon = "⚠️" if is_risky else ""
                
                match_entry = {
                    "Match Details": f"{risk_icon} {target_star_name} ({rashi_simple}) - Pada {t_pada}",
                    "Final Remedied Score": score,
                    "Raw Score": raw_score,
                    "IsRisky": is_risky
                }
                matches.append(match_entry)
            
    # Default Sorting: Raw Score (Highest First) as requested
    return sorted(matches, key=lambda x: x['Raw Score'], reverse=True)

# --- AUTO-DETECT MODEL ---
def get_working_model(key):
    genai.configure(api_key=key)
    try:
        available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        if available: return available[0]
    except: pass
    return "models/gemini-1.5-flash"

def handle_ai_query(prompt, context_str, key):
    try:
        model_name = get_working_model(key); model = genai.GenerativeModel(model_name)
        chat = model.start_chat(history=[{"role": "user", "parts": [context_str]}, {"role": "model", "parts": ["I am your Vedic Astrologer."]}])
        return chat.send_message(prompt).text
    except Exception as e:
        if "429" in str(e): return "⚠️ **Quota Exceeded:** You are clicking too fast! Please wait 60 seconds."
        return f"AI Error: {str(e)}"

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
    pro_mode = st.toggle("✨ Generate Full Horoscopes (Pro Feature)", value=True)
    
    if input_method == "Birth Details":
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 🤵 Boy")
            b_date = st.date_input("Date", datetime.date(1995,1,1), key="b_d")
            b_time = st.time_input("Time", datetime.time(10,0), step=60, key="b_t")
            b_city = st.text_input("City", "Hyderabad", key="b_c")
            b_country = st.text_input("Country", "India", key="b_co")
        with c2:
            st.markdown("### 👰 Girl")
            g_date = st.date_input("Date", datetime.date(1994,11,28), key="g_d")
            g_time = st.time_input("Time", datetime.time(7,35), step=60, key="g_t")
            g_city = st.text_input("City", "Hyderabad", key="g_c")
            g_country = st.text_input("Country", "India", key="g_co")
        st.markdown("---")
    else:
        st.info("ℹ️ **Note:** Advanced Horoscope features are available only with full Birth Details.")
        c1, c2 = st.columns(2)
        with c1:
            b_star = st.selectbox("Boy Star", NAKSHATRAS, key="b_s")
            b_rashi_opts = [RASHIS[i] for i in NAK_TO_RASHI_MAP[NAKSHATRAS.index(b_star)]]
            b_rashi_sel = st.selectbox("Boy Rashi", b_rashi_opts, key="b_r")
            b_pada_sel = st.selectbox("Boy Pada", [1, 2, 3, 4], key="b_p")
        with c2:
            g_star = st.selectbox("Girl Star", NAKSHATRAS, index=11, key="g_s")
            g_rashi_opts = [RASHIS[i] for i in NAK_TO_RASHI_MAP[NAKSHATRAS.index(g_star)]]
            try: g_def_idx = next(i for i, r in enumerate(g_rashi_opts) if "Virgo" in r)
            except StopIteration: g_def_idx = 0
            g_rashi_sel = st.selectbox("Girl Rashi", g_rashi_opts, index=g_def_idx, key="g_r")
            g_pada_sel = st.selectbox("Girl Pada", [1, 2, 3, 4], index=2, key="g_p")

    if st.button("Check Compatibility", type="primary", use_container_width=True):
        try:
            with st.spinner("Analyzing..."):
                b_planets, g_planets, b_d9, g_d9 = None, None, None, None
                b_d9_rashi, g_d9_rashi = None, None
                b_dasha_name, b_dasha_tone = "Unknown", ""
                g_dasha_name, g_dasha_tone = "Unknown", ""
                b_mars_result, g_mars_result = ("Skipped", "No Data"), ("Skipped", "No Data")
                
                if input_method == "Birth Details":
                    b_moon, b_mars_l, _, _, b_chart, b_d9 = get_planetary_positions(b_date, b_time, b_city, b_country, detailed=pro_mode)
                    g_moon, g_mars_l, _, _, g_chart, g_d9 = get_planetary_positions(g_date, g_time, g_city, g_country, detailed=pro_mode)
                    b_nak, b_rashi, b_pada = get_nak_rashi_pada(b_moon)
                    g_nak, g_rashi, g_pada = get_nak_rashi_pada(g_moon)
                    
                    b_d9_rashi = calculate_d9_position(b_moon)
                    g_d9_rashi = calculate_d9_position(g_moon)
                    b_planets, g_planets = b_chart, g_chart
                    b_mars_result = check_mars_dosha_smart(b_rashi, b_mars_l)
                    g_mars_result = check_mars_dosha_smart(g_rashi, g_mars_l)
                    if pro_mode:
                        b_dasha_name, b_dasha_tone = calculate_current_dasha(b_moon, b_date)
                        g_dasha_name, g_dasha_tone = calculate_current_dasha(g_moon, g_date)
                else:
                    b_nak = NAKSHATRAS.index(b_star); b_rashi = RASHIS.index(b_rashi_sel)
                    g_nak = NAKSHATRAS.index(g_star); g_rashi = RASHIS.index(g_rashi_sel)
                    
                    # Direct Mode D9 Calculation
                    b_d9_rashi = get_d9_rashi_from_pada(b_nak, b_pada_sel)
                    g_d9_rashi = get_d9_rashi_from_pada(g_nak, g_pada_sel)
                    
                    b_mars = (False, "Unknown"); g_mars = (False, "Unknown")
                    # For display in report (direct mode)
                    b_pada = b_pada_sel
                    g_pada = g_pada_sel

                score, breakdown, logs, rajju, vedha, safety_override = calculate_all(b_nak, b_rashi, g_nak, g_rashi, b_d9_rashi, g_d9_rashi)
                raw_score = sum(row[1] for row in breakdown)
                
                b_obs, g_obs = [], []
                if pro_mode and b_planets:
                    b_obs = analyze_aspects_and_occupation_rich(b_planets, b_rashi)
                    g_obs = analyze_aspects_and_occupation_rich(g_planets, g_rashi)
                
                human_verdict = generate_human_verdict(score, rajju, b_obs, g_obs, f"{b_dasha_name} ({b_dasha_tone})", f"{g_dasha_name} ({g_dasha_tone})")
                
                # Store friendly names
                b_rashi_name = RASHIS[b_rashi].split(" ")[0]
                g_rashi_name = RASHIS[g_rashi].split(" ")[0]

                st.session_state.results = {
                    "score": score, "raw_score": raw_score, "bd": breakdown, "logs": logs, 
                    "b_n": NAKSHATRAS[b_nak], "g_n": NAKSHATRAS[g_nak],
                    "b_info": f"{NAKSHATRAS[b_nak]} ({b_rashi_name}, Pada {b_pada})",
                    "g_info": f"{NAKSHATRAS[g_nak]} ({g_rashi_name}, Pada {g_pada})",
                    "b_mars": b_mars_result, "g_mars": g_mars_result,
                    "rajju": rajju, "vedha": vedha,
                    "b_planets": b_planets, "g_planets": g_planets,
                    "b_d9": b_d9, "g_d9": g_d9,
                    "verdict": human_verdict, "b_obs": b_obs, "g_obs": g_obs,
                    "b_dasha": f"{b_dasha_name}", "g_dasha": f"{g_dasha_name}",
                    "safety": safety_override
                }
                st.session_state.calculated = True
                st.session_state.ai_pitch = ""
        except Exception as e: st.error(f"Error: {e}")

    if st.session_state.calculated:
        res = st.session_state.results
        st.markdown("---")
        score_val = res['score']; score_color = "#ff4b4b"
        if score_val >= 18: score_color = "#ffa500"
        if score_val >= 25: score_color = "#00cc00"
        
        # Override Color if Risky
        if res.get('safety') == "Risky Match ❌":
            score_color = "#ff4b4b" # Force Red

        c1, c2 = st.columns([1, 1])
        with c1:
             st.markdown(f"<div class='gauge-title' style='color:#888;'>Base Score</div>", unsafe_allow_html=True)
             fig_base = go.Figure(go.Indicator(
                mode = "gauge+number", value = res['raw_score'],
                gauge = {'axis': {'range': [0, 36]}, 'bar': {'color': "#cccccc"}}
            ))
             fig_base.update_layout(height=180, margin=dict(l=30, r=30, t=10, b=10)) 
             st.plotly_chart(fig_base, use_container_width=True)

        with c2:
             st.markdown(f"<div class='gauge-title' style='color:{score_color};'>Remedied Score</div>", unsafe_allow_html=True)
             fig_rem = go.Figure(go.Indicator(
                mode = "gauge+number", value = res['score'],
                gauge = {'axis': {'range': [0, 36]}, 'bar': {'color': score_color}}
            ))
             fig_rem.update_layout(height=180, margin=dict(l=30, r=30, t=10, b=10))
             st.plotly_chart(fig_rem, use_container_width=True)

        st.markdown("##### 🛡️ Applied Remedies (Dosha Bhanga)")
        if res['logs']:
            df_remedies = pd.DataFrame(res['logs'])
            st.dataframe(df_remedies, hide_index=True, use_container_width=True)
        else:
            st.info("No special cancellations (remedies) were needed. The Base Score is the Final Score.")

        status = "Excellent Match ✅" if res['score'] > 24 else ("Good Match ⚠️" if res['score'] > 18 else "Not Recommended ❌")
        
        # Override Status if Risky
        if res.get('safety') == "Risky Match ❌":
            status = "Risky Match ❌ (Zero Bhakoot + Zero Nadi)"
        
        st.markdown(f"""
        <div style="background-color: {score_color}20; border: 2px solid {score_color}; padding: 10px; border-radius: 10px; margin-top: 10px; text-align: center;">
            <h3 style="color: {score_color}; margin: 0; font-size: 24px;">{status}</h3>
        </div>
        """, unsafe_allow_html=True)

        share_text = f"Match Report: {res['b_info']} w/ {res['g_info']}. Score: {res['score']}/36. {status}"
        st.code(share_text, language="text")
        st.caption("👆 Copy to share on WhatsApp")
        
        st.markdown(f"""
        <div class="verdict-box">
            <div class="verdict-title">🤖 AI Astrologer's Verdict</div>
            {res['verdict']}
        </div>
        """, unsafe_allow_html=True)
        
        if res.get('b_planets') and res.get('g_planets'):
            st.markdown("### 🌌 Chart Synergy & Elevator Pitch")
            shared_links = get_shared_positions(res['b_planets'], res['g_planets'])
            if shared_links:
                st.info("🔗 **Cosmic Links Found:**\n" + "\n".join([f"- {s}" for s in shared_links]))
            
            if st.session_state.ai_pitch:
                st.markdown(f"""<div class="synergy-box"><strong>✨ Karmic Connection (AI Insight):</strong><br>{st.session_state.ai_pitch}</div>""", unsafe_allow_html=True)
            
            if st.session_state.api_key:
                if st.button("🔮 Reveal Karmic Connection (AI)"):
                    with st.spinner("Channeling cosmic wisdom..."):
                        b_str = format_chart_for_ai(res['b_planets'])
                        g_str = format_chart_for_ai(res['g_planets'])
                        prompt = f"""
                        Act as an expert Vedic Astrologer. Compare these two charts:
                        Boy: {b_str}
                        Girl: {g_str}
                        Write a 3-4 sentence 'elevator pitch' summarizing the core dynamic, spiritual potential, and karmic connection between them. Focus on the 'Why', not just the 'What'.
                        """
                        pitch = handle_ai_query(prompt, "You are a Vedic Astrologer.", st.session_state.api_key)
                        st.session_state.ai_pitch = pitch
                        st.rerun()
            else:
                st.caption("🔒 *Add API Key in 'Guru AI' tab to unlock the detailed spiritual elevator pitch.*")

        if res.get('b_planets') and res.get('g_planets'):
            st.markdown("### 🔮 Pro: Planetary Charts")
            c1, c2 = st.columns(2)
            with c1: st.markdown(render_south_indian_chart(res['b_planets'], "Boy D1"), unsafe_allow_html=True)
            with c2: st.markdown(render_south_indian_chart(res['g_planets'], "Girl D1"), unsafe_allow_html=True)
            if res.get('b_d9') and res.get('g_d9'):
                st.markdown("---")
                st.markdown("**2. Navamsa Chakra (D9)**")
                c3, c4 = st.columns(2)
                with c3: st.markdown(render_south_indian_chart(res['b_d9'], "Boy D9"), unsafe_allow_html=True)
                with c4: st.markdown(render_south_indian_chart(res['g_d9'], "Girl D9"), unsafe_allow_html=True)
        elif input_method == "Birth Details" and not res.get('b_planets'):
            st.info("💡 Tip: Enable 'Generate Full Horoscopes' to see visual charts.")

        st.markdown("### 📋 Quick Scan")
        for item in res['bd']:
            attr, raw, final, max_pts, reason = item
            border_class = "border-green" if final == max_pts else ("border-orange" if final > 0 else "border-red")
            text_class = "text-green" if final == max_pts else ("text-orange" if final > 0 else "text-red")
            st.markdown(f"""<div class="guna-card {border_class}"><div class="guna-header"><span>{attr}</span><span class="guna-score {text_class}">{final} / {max_pts}</span></div><div class="guna-reason">{reason}</div></div>""", unsafe_allow_html=True)
            
        with st.expander("📊 Detailed Transparency Table (Raw vs Final)"):
            df = pd.DataFrame(res['bd'], columns=["Attribute", "Raw Score", "Final Remedied Score", "Max", "Logic"])
            totals = pd.DataFrame([["TOTAL", df["Raw Score"].sum(), df["Final Remedied Score"].sum(), 36, "-"]], columns=df.columns)
            st.table(pd.concat([df, totals], ignore_index=True))
        
        with st.expander("🪐 Mars & Dosha Analysis"):
            st.write(f"**Rajju:** {res['rajju']} (Body Check)"); st.write(f"**Vedha:** {res['vedha']} (Enemy Check)")
            bm = res['b_mars'][1] if isinstance(res['b_mars'], tuple) else res['b_mars']
            gm = res['g_mars'][1] if isinstance(res['g_mars'], tuple) else res['g_mars']
            st.write(f"**Boy Mars:** {bm}"); st.write(f"**Girl Mars:** {gm}")
            b_is_dosha = res['b_mars'][0] if isinstance(res['b_mars'], tuple) else False
            g_is_dosha = res['g_mars'][0] if isinstance(res['g_mars'], tuple) else False
            if b_is_dosha and g_is_dosha: st.success("🔥➕🔥 **Perfect Match:** Both have high energy (Manglik). Your intensities match perfectly.")
            elif not b_is_dosha and not g_is_dosha: st.success("✨➕✨ **Calm Match:** Both have peaceful Mars placements. A gentle relationship.")
            else: st.warning("🔥⚡✨ **Energy Mismatch:** One is High Intensity, one is Calm. This often requires active adjustment.")

    try:
        if st.button("📄 Download Full Report"):
            pdf_bytes = generate_pdf(res)
            st.download_button("Click to Save PDF", data=pdf_bytes, file_name="Vedic_Match_Report.pdf", mime="application/pdf")
    except Exception as e: st.error(f"PDF Error: {e}")

# --- OTHER TABS ---
with tabs[1]:
    st.header("🔍 Match Finder"); st.caption("Find the best compatible stars for you.")
    
    # Sort Controls
    c_sort1, c_sort2 = st.columns(2)
    with c_sort1:
        show_risky = st.checkbox("Show Risky Matches (Caution!)", value=False)
    with c_sort2:
        sort_order = st.radio("Sort Results By:", ["Remedied Score (Highest First)", "Raw Score (Lowest First)", "Raw Score (Highest First)"], index=2, horizontal=True)
    
    col_f1, col_f2 = st.columns(2)
    with col_f1: 
        finder_gender = st.selectbox("I am a", ["Boy", "Girl"], index=1)
        finder_star = st.selectbox("My Star", NAKSHATRAS, index=11)
        finder_pada = st.selectbox("My Pada", [1, 2, 3, 4], index=2, key="f_p") # Default to 3 (Index 2)
    with col_f2: 
        finder_rashi_opts = [RASHIS[i] for i in NAK_TO_RASHI_MAP[NAKSHATRAS.index(finder_star)]]
        
        # Auto-select Virgo (Kanya) if available, else first
        def_rashi_index = 0
        for i, r in enumerate(finder_rashi_opts):
            if "Virgo" in r:
                def_rashi_index = i
                break
                
        finder_rashi = st.selectbox("My Rashi", finder_rashi_opts, index=def_rashi_index)
        
    if st.button("Find Best Matches", type="primary"):
        with st.spinner("Scanning..."):
            matches = find_best_matches(finder_gender, NAKSHATRAS.index(finder_star), RASHIS.index(finder_rashi), finder_pada)
            
            # Filter Risky Matches Logic
            filtered_matches = []
            for m in matches:
                if m['IsRisky'] and not show_risky:
                    continue # Skip risky unless toggle is on
                filtered_matches.append(m)
            
            # Apply Sorting
            if sort_order == "Raw Score (Lowest First)":
                filtered_matches = sorted(filtered_matches, key=lambda x: x['Raw Score'])
            elif sort_order == "Raw Score (Highest First)":
                filtered_matches = sorted(filtered_matches, key=lambda x: x['Raw Score'], reverse=True)
            else: # Remedied Score (Highest First)
                filtered_matches = sorted(filtered_matches, key=lambda x: x['Final Remedied Score'], reverse=True)
                
            st.success(f"Found {len(filtered_matches)} combinations!"); st.markdown("### Top Matches")
            
            # Export CSV
            if filtered_matches:
                df_export = pd.DataFrame(filtered_matches)
                csv_data = to_csv(df_export)
                st.download_button(label="📥 Download Results as CSV", data=csv_data, file_name="match_results.csv", mime="text/csv")

            # Render Table (HTML - No Indentation Trick)
            if filtered_matches:
                table_html = "<table style='width:100%; border-collapse: collapse; font-family: sans-serif; font-size: 14px;'>"
                table_html += "<thead><tr style='background-color: #f0f2f6; color: #333333; border-bottom: 2px solid #ccc;'>"
                table_html += "<th style='padding: 10px; text-align: left; width: 60%;'>Match Details</th>"
                table_html += "<th style='padding: 10px; text-align: center; width: 20%;'>Raw<br>Score</th>"
                table_html += "<th style='padding: 10px; text-align: center; width: 20%;'>Remedied<br>Score</th></tr></thead>"
                table_html += "<tbody>"
                
                for m in filtered_matches:
                    bg_style = "background-color: #ffe6e6;" if m['IsRisky'] else ""
                    table_html += f"<tr style='border-bottom: 1px solid #eee; {bg_style}'>"
                    table_html += f"<td style='padding: 10px; text-align: left; word-wrap: break-word;'>{m['Match Details']}</td>"
                    table_html += f"<td style='padding: 10px; text-align: center;'>{m['Raw Score']}</td>"
                    table_html += f"<td style='padding: 10px; text-align: center; font-weight: bold;'>{m['Final Remedied Score']}</td></tr>"
                
                table_html += "</tbody></table>"
                st.markdown(table_html, unsafe_allow_html=True)
            else:
                st.warning("No matches found with current filters. Try enabling 'Show Risky Matches'.")

with tabs[2]:
    st.header("💍 Wedding Dates"); t_rashi = st.selectbox("Select Moon Sign (Rashi)", RASHIS, key="t_r")
    if st.button("Check Auspicious Dates"):
        r_idx = RASHIS.index(t_rashi); st.subheader("Lucky Years")
        for y, s in predict_marriage_luck_years(r_idx): st.write(f"**{y}:** {s}")
        st.subheader("Lucky Month"); st.info(f"❤️ **{predict_wedding_month(r_idx)}**")

with tabs[3]:
    st.header("🤖 Guru AI"); 
    if st.secrets.get("GEMINI_API_KEY"):
        st.success("✅ API Key Loaded from System Secrets")
        if not st.session_state.api_key: st.session_state.api_key = st.secrets["GEMINI_API_KEY"]
    else:
        user_key = st.text_input("API Key (aistudio.google.com)", type="password", value=st.session_state.api_key)
        if user_key: st.session_state.api_key = user_key
    
    if st.button("🗑️ Clear Chat History"):
        st.session_state.messages = []
        st.rerun()
        
    context = "You are a Vedic Astrologer."
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
