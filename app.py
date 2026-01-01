import streamlit as st
import ephem
import datetime
import math
import pytz
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
from fpdf import FPDF
from io import BytesIO
import base64
import json

# ==========================================
# 1. GLOBAL SETTINGS & THEME
# ==========================================
st.set_page_config(
    page_title="Vedic Matcher Pro v2026 | Enterprise Edition",
    page_icon="🕉️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Premium UI
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700&family=Inter:wght@300;400;600;800&display=swap');
    
    :root {
        --gold: #D4AF37;
        --royal-blue: #1e293b;
        --bg-subtle: #f8fafc;
    }

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: white; }

    /* Hide UI Overlays */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Typography */
    .brand-title { 
        font-family: 'Cinzel', serif; 
        color: var(--royal-blue); 
        text-align: center; 
        font-size: 3.5rem; 
        font-weight: 700;
        margin-bottom: 0px;
    }
    .brand-subtitle {
        text-align: center;
        color: #64748b;
        font-size: 1.2rem;
        margin-bottom: 30px;
        letter-spacing: 2px;
    }

    /* Guna Cards */
    .guna-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 15px;
        border: 1px solid #e2e8f0;
        border-left: 6px solid #94a3b8;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
        transition: all 0.3s ease;
    }
    .guna-card:hover { transform: translateY(-3px); box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); }
    .card-header { display: flex; justify-content: space-between; align-items: center; }
    .card-title { font-weight: 800; text-transform: uppercase; font-size: 0.9rem; color: #475569; }
    .card-score { font-size: 1.4rem; font-weight: 800; }
    .card-desc { font-size: 0.85rem; color: #64748b; margin-top: 10px; line-height: 1.5; }

    /* Custom Borders based on Status */
    .status-pass { border-left-color: #10b981 !important; color: #10b981 !important; }
    .status-warn { border-left-color: #f59e0b !important; color: #f59e0b !important; }
    .status-fail { border-left-color: #ef4444 !important; color: #ef4444 !important; }

    /* Chart Containers */
    .chart-panel {
        background: var(--royal-blue);
        border-radius: 16px;
        padding: 20px;
        color: white;
        text-align: center;
    }
    
    /* Metrics Styling */
    [data-testid="stMetricValue"] { font-weight: 800; color: var(--royal-blue); }

    /* AI Box */
    .ai-insight {
        background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
        border: 1px solid #bae6fd;
        border-radius: 16px;
        padding: 25px;
        margin: 20px 0;
        color: #0369a1;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CONSTANTS & METADATA (Vedic Database)
# ==========================================

NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta",
    "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
]

RASHIS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
RASHI_LORDS = [2, 5, 3, 1, 0, 3, 5, 2, 4, 6, 6, 4] # Sun:0...Sat:6
PLANETS = {0: "Sun", 1: "Moon", 2: "Mars", 3: "Mercury", 4: "Jupiter", 5: "Venus", 6: "Saturn", 7: "Rahu", 8: "Ketu"}

# Ashta Koota Matrices
GANA_LIST = [0, 1, 2, 1, 0, 1, 0, 0, 2, 2, 1, 1, 0, 2, 0, 2, 0, 2, 2, 1, 1, 0, 2, 2, 1, 1, 0]
NADI_LIST = [0, 1, 2, 2, 1, 0, 0, 1, 2, 2, 1, 0, 0, 1, 2, 2, 1, 0, 0, 1, 2, 2, 1, 0, 0, 1, 2]
YONI_LIST = [0, 1, 2, 3, 3, 4, 5, 2, 5, 6, 6, 7, 8, 9, 8, 9, 10, 10, 4, 11, 12, 11, 13, 0, 13, 7, 1]
YONI_NAMES = ["Horse", "Elephant", "Ram", "Snake", "Dog", "Cat", "Rat", "Cow", "Buffalo", "Tiger", "Deer", "Monkey", "Mongoose", "Lion"]
YONI_ENEMIES = {0:8, 1:13, 2:11, 3:12, 4:10, 5:6, 6:5, 7:9, 8:0, 9:7, 10:4, 11:2, 12:3, 13:1}

VARNA_LIST = [1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0] # 0:Brahmin, 1:Kshatriya, 2:Vaishya, 3:Shudra
VASHYA_LIST = [0, 0, 1, 2, 0, 1, 1, 3, 0, 2, 1, 2] # 0:Quadruped, 1:Human, 2:Water, 3:Insect

MAITRI_MATRIX = [
    [5, 5, 5, 4, 5, 0, 0], # Sun
    [5, 5, 4, 5, 4, 1, 1], # Moon
    [5, 4, 5, 0.5, 5, 3, 0.5], # Mars
    [4, 1, 0.5, 5, 0.5, 5, 4], # Mercury
    [5, 4, 5, 0.5, 5, 0.5, 3], # Jupiter
    [0, 1, 3, 5, 0.5, 5, 5], # Venus
    [0, 1, 0.5, 4, 3, 5, 5]  # Saturn
]

# ==========================================
# 3. EPHEMERIS & CALCULATIONS
# ==========================================

@st.cache_resource
def init_geo(): return Nominatim(user_agent="vedic_matcher_pro_2026"), TimezoneFinder()

def get_ayana(jd):
    """Lahiri Ayanamsa Calculation."""
    return 23.85 + (1.396 * (jd - 2451545.0) / 36525.0)

def calculate_horoscope(dob, tob, city, country):
    geolocator, tf = init_geo()
    dt_naive = datetime.datetime.combine(dob, tob)
    
    try:
        loc = geolocator.geocode(f"{city}, {country}")
        tz_str = tf.timezone_at(lng=loc.longitude, lat=loc.latitude)
        tz = pytz.timezone(tz_str)
        offset = tz.localize(dt_naive).utcoffset().total_seconds() / 3600.0
    except:
        offset = 5.5
        loc = type('obj', (object,), {'latitude': 28.6, 'longitude': 77.2})()
        tz_str = "Asia/Kolkata"

    obs = ephem.Observer()
    obs.lat, obs.lon = str(loc.latitude), str(loc.longitude)
    obs.date = dt_naive - datetime.timedelta(hours=offset)
    jd = ephem.julian_date(obs.date)
    aya = get_ayana(jd)

    planets_data = {}
    for pid, name in PLANETS.items():
        if pid < 7: # Physical planets
            body = getattr(ephem, name)()
            body.compute(obs)
            long = (math.degrees(ephem.Ecliptic(body).lon) - aya) % 360
            planets_data[name] = long
    
    # Rahu / Ketu
    t = (jd - 2451545.0) / 36525.0
    rahu = (125.04452 - 1934.136261 * t - aya) % 360
    planets_data["Rahu"] = rahu
    planets_data["Ketu"] = (rahu + 180) % 360

    # Lagna (Ascendant)
    ra_l, dec_l = obs.radec_of(0, "90")
    obl = math.radians(23.439)
    phi = math.radians(float(obs.lat))
    sidereal = float(obs.sidereal_time())
    y = math.sin(sidereal)
    x = math.cos(sidereal)*math.cos(obl) - math.tan(phi)*math.sin(obl)
    lagna = (math.degrees(math.atan2(y, x)) - aya) % 360
    planets_data["Lagna"] = lagna

    # D9 Navamsa
    d9_data = {}
    for p, long in planets_data.items():
        r_idx = int(long / 30)
        nav_idx = int((long % 30) / (3.333333))
        # Navamsa sequence starts from Aries, Sagittarius, Leo, or Aries
        starts = [0, 8, 4, 0, 8, 4, 0, 8, 4, 0, 8, 4]
        d9_data[p] = (starts[r_idx] + nav_idx) % 12

    return planets_data, d9_data, tz_str

# ==========================================
# 4. COMPATIBILITY ENGINE (GUNA MILAN)
# ==========================================

def perform_guna_milan(b_pos, g_pos):
    b_moon, g_moon = b_pos["Moon"], g_pos["Moon"]
    b_nak, g_nak = int(b_moon / 13.333333), int(g_moon / 13.333333)
    b_ras, g_ras = int(b_moon / 30), int(g_moon / 30)
    
    res = {}
    logs = []

    # 1. Varna (1)
    bv, gv = VARNA_LIST[b_ras], VARNA_LIST[g_ras]
    res["Varna"] = (1 if bv >= gv else 0, 1, "Spiritual/Social Compatibility")
    
    # 2. Vashya (2)
    bva, gva = VASHYA_LIST[b_ras], VASHYA_LIST[g_ras]
    v_score = 2 if bva == gva else (1 if (bva in [0,1] and gva in [0,1]) else 0)
    res["Vashya"] = (v_score, 2, "Power Dynamics & Dominance")

    # 3. Tara (3)
    t_diff = (g_nak - b_nak) % 9
    t_score = 3 if t_diff in [0, 1, 2, 4, 6, 8] else 1.5
    res["Tara"] = (t_score, 3, "Inter-destiny & Fortune")

    # 4. Yoni (4)
    by, gy = YONI_LIST[b_nak], YONI_LIST[g_nak]
    y_score = 4 if by == gy else (0 if YONI_ENEMIES.get(by) == gy else 2)
    res["Yoni"] = (y_score, 4, "Physical & Biological Synergy")

    # 5. Maitri (5)
    bl, gl = RASHI_LORDS[b_ras], RASHI_LORDS[g_ras]
    m_score = MAITRI_MATRIX[bl][gl]
    res["Maitri"] = (m_score, 5, "Friendship between Moon Lords")

    # 6. Gana (6)
    bg, gg = GANA_LIST[b_nak], GANA_LIST[g_nak]
    if bg == gg: g_score = 6
    elif (bg == 0 and gg == 1) or (bg == 1 and gg == 0): g_score = 5
    elif (bg == 0 and gg == 2) or (bg == 2 and gg == 0): g_score = 1
    else: g_score = 0
    res["Gana"] = (g_score, 6, "Temperamental Compatibility")

    # 7. Bhakoot (7)
    dist = (g_ras - b_ras) % 12 + 1
    bh_score = 0 if dist in [2, 12, 5, 9, 6, 8] else 7
    res["Bhakoot"] = (bh_score, 7, "Prosperity & Family Welfare")

    # 8. Nadi (8)
    bn, gn = NADI_LIST[b_nak], NADI_LIST[g_nak]
    n_score = 8 if bn != gn else 0
    res["Nadi"] = (n_score, 8, "Genetic & Health Compatibility")

    # Dosha Bhanga (Cancellations)
    remedied_res = {k: v[0] for k, v in res.items()}
    if remedied_res["Bhakoot"] == 0 and m_score >= 4:
        remedied_res["Bhakoot"] = 7
        logs.append("Bhakoot Dosha cancelled: Strong planetary friendship.")
    if remedied_res["Nadi"] == 0 and (b_ras == g_ras or m_score == 5):
        remedied_res["Nadi"] = 8
        logs.append("Nadi Dosha cancelled: Identical Rashi or Supreme Maitri.")

    raw_sum = sum(v[0] for v in res.values())
    rem_sum = sum(remedied_res.values())

    return raw_sum, rem_sum, res, remedied_res, logs

# ==========================================
# 5. KUJA DOSHA (MANGLIK) ADVANCED
# ==========================================

def analyze_kuja_dosha(pos):
    """Professional triple-check for Mars intensity."""
    houses = [1, 2, 4, 7, 8, 12]
    total_score = 0
    details = []
    
    for ref in ["Lagna", "Moon", "Venus"]:
        ref_long = pos[ref]
        m_long = pos["Mars"]
        house = (int(m_long/30) - int(ref_long/30)) % 12 + 1
        if house in houses:
            # Check for cancellations
            m_rashi = int(m_long/30)
            if m_rashi in [0, 7]: detail = f"Mars in {house} from {ref} (Neutralized: Own House)"
            elif m_rashi == 9: detail = f"Mars in {house} from {ref} (Neutralized: Exalted)"
            else:
                total_score += (1 if ref == "Lagna" else 0.5)
                detail = f"Mars in {house} from {ref} (Active)"
            details.append(detail)
            
    status = "None" if total_score == 0 else ("High" if total_score >= 1.5 else "Partial")
    return status, total_score, details

# ==========================================
# 6. VISUALIZATION (CHARTS & PDF)
# ==========================================

def generate_south_chart_svg(pos, title):
    # Mapping Rashi to Grid positions
    mapping = {11:0, 0:1, 1:2, 2:3, 10:4, 3:7, 9:8, 4:11, 8:12, 7:13, 6:14, 5:15}
    cells = [""] * 16
    for p, long in pos.items():
        r = int(long/30)
        cells[mapping[r]] += f"{p[:2]} "
        
    svg = f'<svg width="300" height="300" viewBox="0 0 400 400" xmlns="http://www.w3.org/2000/svg">'
    svg += f'<rect width="400" height="400" fill="#1e293b" rx="10"/>'
    for i in range(16):
        if i in [5,6,9,10]: continue
        row, col = i // 4, i % 4
        x, y = col * 100, row * 100
        svg += f'<rect x="{x+2}" y="{y+2}" width="96" height="96" fill="#334155" rx="5"/>'
        svg += f'<text x="{x+50}" y="{y+55}" fill="#f1f5f9" font-size="14" font-weight="bold" text-anchor="middle">{cells[i]}</text>'
    svg += f'<text x="200" y="210" fill="#94a3b8" font-size="16" text-anchor="middle" font-weight="bold">{title}</text>'
    svg += '</svg>'
    return svg

def create_report_pdf(b_name, g_name, score, res_table, ai_text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 20)
    pdf.cell(200, 10, "Vedic Matchmaking Professional Report", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, f"Match: {b_name} & {g_name}", ln=True)
    pdf.cell(200, 10, f"Final Score: {score}/36", ln=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(40, 10, "Attribute", 1)
    pdf.cell(30, 10, "Score", 1)
    pdf.cell(120, 10, "Analysis", 1)
    pdf.ln()
    
    pdf.set_font("Arial", '', 10)
    for k, v in res_table.items():
        pdf.cell(40, 10, k, 1)
        pdf.cell(30, 10, f"{v[0]}/{v[1]}", 1)
        pdf.cell(120, 10, v[2], 1)
        pdf.ln()
        
    if ai_text:
        pdf.ln(10)
        pdf.set_font("Arial", 'I', 11)
        pdf.multi_cell(0, 7, f"AI Insight: {ai_text}")
        
    return pdf.output(dest='S').encode('latin-1', 'replace')

# ==========================================
# 7. MAIN APPLICATION UI
# ==========================================

def main():
    st.markdown("<h1 class='brand-title'>Vedic Matcher Pro</h1>", unsafe_allow_html=True)
    st.markdown("<p class='brand-subtitle'>ANCIENT WISDOM x MODERN PRECISION</p>", unsafe_allow_html=True)

    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2312/2312443.png", width=80)
        st.title("Control Panel")
        api_key = st.text_input("Gemini API Key", type="password")
        st.divider()
        st.markdown("### Report Settings")
        pdf_enabled = st.checkbox("Generate PDF Report", value=True)
        chart_style = st.selectbox("Chart Style", ["South Indian", "North Indian (Beta)"])
        st.divider()
        st.caption("v.2026.01-Enterprise")

    tab_input, tab_result, tab_finder = st.tabs(["📥 Input Details", "📊 Analysis Report", "🔍 Global Finder"])

    with tab_input:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 🤵 Groom (Boy)")
            b_name = st.text_input("Groom's Name", "Arjun")
            b_dob = st.date_input("Date of Birth", datetime.date(1994, 5, 20))
            b_tob = st.time_input("Time of Birth", datetime.time(14, 30))
            b_city = st.text_input("Birth City", "Mumbai")
            b_country = st.text_input("Country", "India", key="b_co")
            
        with col2:
            st.markdown("### 👰 Bride (Girl)")
            g_name = st.text_input("Bride's Name", "Priya")
            g_dob = st.date_input("Date of Birth ", datetime.date(1995, 11, 12))
            g_tob = st.time_input("Time of Birth ", datetime.time(9, 15))
            g_city = st.text_input("Birth City ", "Pune")
            g_country = st.text_input("Country ", "India", key="g_co")

        calc_btn = st.button("🌟 REVEAL COSMIC COMPATIBILITY", use_container_width=True)

    if calc_btn:
        with st.spinner("Processing Stellar Positions..."):
            # Core Computations
            b_pos, b_d9, b_tz = calculate_horoscope(b_dob, b_tob, b_city, b_country)
            g_pos, g_d9, g_tz = calculate_horoscope(g_dob, g_tob, g_city, g_country)
            
            raw, rem, data, remedied_data, logs = perform_guna_milan(b_pos, g_pos)
            b_mang_status, b_mang_val, b_mang_details = analyze_kuja_dosha(b_pos)
            g_mang_status, g_mang_val, g_mang_details = analyze_kuja_dosha(g_pos)

            # Store in session state for cross-tab access
            st.session_state.match_results = {
                "b_name": b_name, "g_name": g_name, "score": rem, "raw": raw,
                "data": data, "remedied": remedied_data, "logs": logs,
                "b_pos": b_pos, "g_pos": g_pos, "b_mang": b_mang_status, "g_mang": g_mang_status
            }

            with tab_result:
                # Dashboard Summary
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Match Score", f"{rem}/36")
                m2.metric("Compatibility", "Excellent" if rem >= 25 else ("Good" if rem >= 18 else "Challenging"))
                m3.metric(f"{b_name} Manglik", b_mang_status)
                m4.metric(f"{g_name} Manglik", g_mang_status)

                # Charts
                st.divider()
                c_col1, c_col2 = st.columns(2)
                with c_col1:
                    st.write(generate_south_chart_svg(b_pos, f"{b_name} D1"), unsafe_allow_html=True)
                with c_col2:
                    st.write(generate_south_chart_svg(g_pos, f"{g_name} D1"), unsafe_allow_html=True)

                # Guna Breakdown
                st.subheader("📋 Detailed Koota Breakdown")
                k_cols = st.columns(4)
                for idx, (k, v) in enumerate(data.items()):
                    score = remedied_data[k]
                    status = "pass" if score == v[1] else ("warn" if score > 0 else "fail")
                    k_cols[idx % 4].markdown(f"""
                    <div class="guna-card status-{status}">
                        <div class="card-header">
                            <span class="card-title">{k}</span>
                            <span class="card-score">{score}/{v[1]}</span>
                        </div>
                        <p class="card-desc">{v[2]}</p>
                    </div>
                    """, unsafe_allow_html=True)

                if logs:
                    st.success("🛡️ **Dosha Cancellations (Remedies) Found:**\n" + "\n".join([f"- {l}" for l in logs]))

                # AI Synthesis
                ai_pitch = ""
                if api_key:
                    try:
                        genai.configure(api_key=api_key)
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        prompt = f"Analyze Vedic Match: Groom {b_name} (Manglik: {b_mang_status}), Bride {g_name} (Manglik: {g_mang_status}). Guna Score: {rem}/36. Give 3 paragraphs of psychological and spiritual insight."
                        ai_pitch = model.generate_content(prompt).text
                        st.markdown(f"<div class='ai-insight'><strong>✨ AI Astrologer's Verdict:</strong><br><br>{ai_pitch}</div>", unsafe_allow_html=True)
                    except: st.error("AI service busy.")

                # PDF Export
                if pdf_enabled:
                    pdf_data = create_report_pdf(b_name, g_name, rem, data, ai_pitch)
                    st.download_button("📥 Download PDF Report", pdf_data, f"{b_name}_{g_name}_Match.pdf", "application/pdf")

    with tab_finder:
        st.header("🔍 Star Match Finder")
        st.caption("Find the most compatible moon signs for your birth star.")
        f_col1, f_col2 = st.columns(2)
        with f_col1:
            my_star = st.selectbox("My Birth Nakshatra", NAKSHATRAS)
            my_sex = st.radio("My Gender", ["Male", "Female"])
        
        if st.button("Scan All Stars"):
            my_idx = NAKSHATRAS.index(my_star)
            my_p = {"Moon": my_idx * 13.333 + 6} # Middle of star
            finder_results = []
            for i in range(27):
                target_p = {"Moon": i * 13.333 + 6}
                if my_sex == "Male": _, score, _, _, _ = perform_guna_milan(my_p, target_p)
                else: _, score, _, _, _ = perform_guna_milan(target_p, my_p)
                finder_results.append({"Compatible Star": NAKSHATRAS[i], "Score": score})
            
            df = pd.DataFrame(finder_results).sort_values("Score", ascending=False)
            st.dataframe(df, use_container_width=True, hide_index=True)

# Final Execution
if __name__ == "__main__":
    main()
