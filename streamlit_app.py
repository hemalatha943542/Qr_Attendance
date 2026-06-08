import streamlit as st
import streamlit.components.v1 as components
import qrcode
import io
from datetime import date
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Auxilium College - QR Attendance", page_icon="🎓", layout="wide")

st.markdown("""
<style>
.stApp { background: linear-gradient(135deg, #0a1628 0%, #0d1f3c 50%, #0a1628 100%); }
[data-testid="stSidebar"] { background: linear-gradient(180deg, #0d1f3c 0%, #0a1628 100%) !important; border-right: 2px solid #c9a227; }
h1 { color: #c9a227 !important; }
h2 { color: #e8c547 !important; border-bottom: 2px solid #c9a227; padding-bottom: 8px; }
h3 { color: #c9a227 !important; }
.menu-btn { display: block; width: 100%; padding: 10px 15px; margin: 5px 0; background: linear-gradient(90deg, #0d2a5e, #0a1f4a); color: #f0d060 !important; text-decoration: none !important; border-radius: 8px; font-size: 15px; cursor: pointer; border: 1px solid #c9a227; }
.stButton > button { background: linear-gradient(90deg, #1a3a6b, #0d2a5e) !important; color: #f0d060 !important; border: 1px solid #c9a227 !important; border-radius: 8px !important; font-weight: bold !important; }
.stTextInput > div > div > input { background: #0d1f3c !important; color: #f0d060 !important; border: 1px solid #c9a227 !important; border-radius: 8px !important; }
.stTextInput > label { color: #c9a227 !important; font-weight: bold !important; }
[data-testid="stMetric"] { background: linear-gradient(135deg, #0d1f3c, #1a3a6b) !important; border: 1px solid #c9a227 !important; border-radius: 10px !important; padding: 10px !important; }
[data-testid="stMetricLabel"] { color: #c9a227 !important; }
[data-testid="stMetricValue"] { color: #f0d060 !important; }
hr { border-color: #c9a227 !important; opacity: 0.4; }
p, div, span, label { color: #e0d0a0 !important; }
.college-header { background: linear-gradient(90deg, #0d1f3c, #1a3a6b, #0d1f3c); border: 2px solid #c9a227; border-radius: 12px; padding: 16px; text-align: center; margin-bottom: 20px; }
.college-header h1 { color: #c9a227 !important; font-size: 28px !important; margin: 0 !important; }
.college-header p { color: #f0d060 !important; margin: 4px 0 0 0 !important; font-size: 14px !important; }
</style>
""", unsafe_allow_html=True)

# ===================== GOOGLE SHEETS =====================

SHEET_ID = "1S6dtYyb8fmDGGtwAnXoerQrudv8ZKILxAy67B-37Bu8"
SCOPES = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

@st.cache_resource(ttl=3600)
def get_sheets_client():
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)

@st.cache_resource(ttl=3600)
def get_workbook():
    client = get_sheets_client()
    try:
        return client.open_by_key(SHEET_ID)
    except:
        return client.open("QR_Attendance")

def get_students_sheet():
    wb = get_workbook()
    for ws in wb.worksheets():
        if ws.title.strip().lower() == "students":
            return ws
    ws = wb.add_worksheet(title="Students", rows="1000", cols="5")
    ws.append_row(["ID", "Name", "Roll Number", "Exam Number"])
    return ws

def get_attendance_sheet():
    wb = get_workbook()
    for ws in wb.worksheets():
        if ws.title.strip().lower() == "attendance":
            return ws
    ws = wb.add_worksheet(title="Attendance", rows="10000", cols="4")
    ws.append_row(["Student ID", "Name", "Date", "Status"])
    return ws

@st.cache_data(ttl=60)
def get_students():
    ws = get_students_sheet()
    return [(r["ID"], r["Name"], r["Roll Number"], r["Exam Number"]) for r in ws.get_all_records()]

def add_student(name, roll, exam):
    ws = get_students_sheet()
    rows = ws.get_all_records()
    for r in rows:
        if str(r["Roll Number"]) == str(roll):
            return False
    ws.append_row([len(rows)+1, name, roll, exam])
    get_students.clear()
    return True

def delete_student(sid):
    ws = get_students_sheet()
    try:
        cell = ws.find(str(sid))
        if cell: ws.delete_rows(cell.row)
    except: pass
    aws = get_attendance_sheet()
    rows_to_delete = [i for i,r in enumerate(aws.get_all_records(),2) if str(r["Student ID"])==str(sid)]
    for row in reversed(rows_to_delete): aws.delete_rows(row)
    get_students.clear()

def mark_present_by_roll(roll):
    ws = get_students_sheet()
    student = None
    for r in ws.get_all_records():
        if str(r["Roll Number"]).strip() == str(roll).strip():
            student = r
            break
    if not student:
        return None, "notfound"
    today = str(date.today())
    aws = get_attendance_sheet()
    for i,r in enumerate(aws.get_all_records(),2):
        if str(r["Student ID"])==str(student["ID"]) and r["Date"]==today:
            if r["Status"]=="Absent":
                aws.update_cell(i,4,"Present")
                return student["Name"], "updated"
            else:
                return student["Name"], "already"
    aws.append_row([student["ID"], student["Name"], today, "Present"])
    return student["Name"], "new"

def mark_all_absent():
    ws = get_students_sheet()
    today = str(date.today())
    aws = get_attendance_sheet()
    marked_ids = {str(r["Student ID"]) for r in aws.get_all_records() if r["Date"]==today}
    for s in ws.get_all_records():
        if str(s["ID"]) not in marked_ids:
            aws.append_row([s["ID"], s["Name"], today, "Absent"])

@st.cache_data(ttl=30)
def get_today_summary():
    aws = get_attendance_sheet()
    ws = get_students_sheet()
    today = str(date.today())
    students = {str(s["ID"]): s for s in ws.get_all_records()}
    result = []
    for r in aws.get_all_records():
        if r["Date"]==today:
            s = students.get(str(r["Student ID"]),{})
            result.append((r["Name"], s.get("Roll Number",""), s.get("Exam Number",""), r["Status"]))
    return result

@st.cache_data(ttl=60)
def get_report(filter_date):
    aws = get_attendance_sheet()
    ws = get_students_sheet()
    students = {str(s["ID"]): s for s in ws.get_all_records()}
    result = []
    for r in aws.get_all_records():
        if r["Date"]==str(filter_date):
            s = students.get(str(r["Student ID"]),{})
            result.append((r["Name"], s.get("Roll Number",""), s.get("Exam Number",""), r["Date"], r["Status"]))
    return result

def generate_qr(roll):
    img = qrcode.make(str(roll))
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf

# ===================== SESSION STATE =====================
for key in ['last_scanned','scan_result_name','scan_result_status']:
    if key not in st.session_state:
        st.session_state[key] = ""
if 'scanner_unlocked' not in st.session_state:
    st.session_state.scanner_unlocked = False

# ===================== URL PARAM — QR scan result =====================
qp = st.query_params
scanned_from_url = qp.get("roll", "")
if scanned_from_url and scanned_from_url != st.session_state.last_scanned:
    st.session_state.last_scanned = scanned_from_url
    try:
        name_found, status_val = mark_present_by_roll(scanned_from_url)
        st.session_state.scan_result_name = name_found or scanned_from_url
        st.session_state.scan_result_status = status_val
        get_today_summary.clear()
    except:
        st.session_state.scan_result_name = scanned_from_url
        st.session_state.scan_result_status = "notfound"
    st.query_params.clear()

# ===================== SIDEBAR =====================
with st.sidebar:
    try: st.image("static/auxlogo.jpg", width=120)
    except: st.markdown('<p style="text-align:center;font-size:40px;">🎓</p>', unsafe_allow_html=True)
    st.markdown('<h2 style="text-align:center;color:#c9a227!important;">Auxilium College</h2>', unsafe_allow_html=True)
    st.markdown('<p style="text-align:center;color:#f0d060;font-size:12px;">QR Attendance System</p>', unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("""
    <a class="menu-btn" href="#add-student">➕ Add Student</a>
    <a class="menu-btn" href="#students-list">👥 Students List</a>
    <a class="menu-btn" href="#qr-scanner">📷 QR Scanner</a>
    <a class="menu-btn" href="#today-summary">📋 Today Summary</a>
    <a class="menu-btn" href="#attendance-report">📊 Attendance Report</a>
    """, unsafe_allow_html=True)
    st.markdown("---")
    st.markdown(f'<p style="color:#c9a227;">📅 Today: <b>{date.today()}</b></p>', unsafe_allow_html=True)

st.markdown("""
<div class="college-header">
    <h1>🎓 Auxilium College of Arts & Science</h1>
    <p>📋 QR Attendance Management System | Vellore</p>
</div>
""", unsafe_allow_html=True)
st.markdown("---")

# ===================== ADD STUDENT =====================
st.markdown('<h2 id="add-student">➕ Add Student</h2>', unsafe_allow_html=True)
col1, col2, col3 = st.columns(3)
with col1: sname = st.text_input("Student Name")
with col2: sroll = st.text_input("Roll Number")
with col3: sexam = st.text_input("Exam Number")

if st.button("➕ Add Student & Generate QR", use_container_width=True):
    if sname and sroll:
        if add_student(sname, sroll, sexam):
            st.success(f"✅ {sname} added!")
            st.image(generate_qr(sroll), caption=f"QR - {sname}", width=200)
        else:
            st.error("❌ Roll number already exists!")
    else:
        st.warning("⚠️ Name மற்றும் Roll Number போடுங்க!")

st.markdown("---")

# ===================== STUDENTS LIST =====================
st.markdown('<h2 id="students-list">👥 Students List</h2>', unsafe_allow_html=True)
try:
    students = get_students()
    if students:
        h0,h1,h2,h3,h4,h5 = st.columns([1,2,2,2,2,1])
        h0.markdown("**S.No**"); h1.markdown("**Name**"); h2.markdown("**Roll**")
        h3.markdown("**Exam No**"); h4.markdown("**QR Code**"); h5.markdown("**Delete**")
        st.markdown("---")
        for i,s in enumerate(students,1):
            c0,c1,c2,c3,c4,c5 = st.columns([1,2,2,2,2,1])
            c0.write(i); c1.write(s[1]); c2.write(s[2]); c3.write(s[3] if s[3] else "-")
            with c4: st.image(generate_qr(s[2]), width=80)
            with c5:
                if st.button("🗑️", key=f"d{s[0]}"):
                    delete_student(s[0]); st.rerun()
    else:
        st.info("No students yet!")
except:
    st.warning("⚠️ 1 minute பிறகு refresh பண்ணுங்க")

st.markdown("---")

# ===================== QR SCANNER =====================
st.markdown('<h2 id="qr-scanner">📷 QR Scanner</h2>', unsafe_allow_html=True)

SCANNER_PASSWORD = "auxilium2024"

if not st.session_state.scanner_unlocked:
    st.warning("🔒 Scanner பயன்படுத்த Teacher Password போடுங்கள்!")
    pwd_col1, pwd_col2 = st.columns([3, 1])
    with pwd_col1:
        pwd_input = st.text_input("Password", type="password", key="pwd_input", placeholder="Teacher password உள்ளிடுங்கள்...")
    with pwd_col2:
        st.write(""); st.write("")
        if st.button("🔓 Unlock", use_container_width=True):
            if pwd_input == SCANNER_PASSWORD:
                st.session_state.scanner_unlocked = True
                st.rerun()
            else:
                st.error("❌ தவறான Password!")
else:
    st.info("📱 QR code scan பண்ணினா automatically Present mark ஆகும்!")
    if st.button("🔒 Lock Scanner"):
        st.session_state.scanner_unlocked = False
        st.session_state.scan_result_name = ""
        st.rerun()

    if st.session_state.scan_result_name:
        n = st.session_state.scan_result_name
        s = st.session_state.scan_result_status
        if s == "updated":    st.success(f"✅ {n} — Absent → Present Marked!")
        elif s == "already":  st.info(f"ℹ️ {n} — Already Present!")
        elif s == "new":      st.success(f"✅ {n} — Present Marked! 🎉")
        elif s == "notfound": st.error(f"❌ '{n}' — Student not found!")

    scanner_html = """<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { background:#0a1628; font-family:Arial,sans-serif; }
#container { display:flex; flex-direction:column; align-items:center; padding:16px; gap:12px; }
#video-wrap { position:relative; width:100%; max-width:380px; border-radius:16px; overflow:hidden; border:2px solid #c9a227; box-shadow:0 0 20px rgba(201,162,39,0.5); }
video { width:100%; display:block; border-radius:14px; }
#overlay { position:absolute; top:50%; left:50%; transform:translate(-50%,-50%); width:180px; height:180px; border:3px solid #c9a227; border-radius:12px; box-shadow:0 0 0 9999px rgba(0,0,0,0.35); pointer-events:none; }
.corner { position:absolute; width:22px; height:22px; border-color:#c9a227; border-style:solid; }
.tl { top:-2px;left:-2px; border-width:3px 0 0 3px; border-radius:4px 0 0 0; }
.tr { top:-2px;right:-2px; border-width:3px 3px 0 0; border-radius:0 4px 0 0; }
.bl { bottom:-2px;left:-2px; border-width:0 0 3px 3px; border-radius:0 0 0 4px; }
.br { bottom:-2px;right:-2px; border-width:0 3px 3px 0; border-radius:0 0 4px 0; }
#scan-line { position:absolute; left:4px; right:4px; height:2px; background:linear-gradient(90deg,transparent,#e8c547,transparent); animation:scan 2s linear infinite; top:10%; }
@keyframes scan { 0%{top:10%} 50%{top:85%} 100%{top:10%} }
#status { width:100%; max-width:380px; padding:12px 16px; border-radius:10px; font-size:15px; text-align:center; font-weight:bold; background:#0d1f3c; color:#f0d060; border:1px solid #c9a227; min-height:48px; }
#status.success { background:#052e16; color:#4ade80; border-color:#166534; }
#status.error { background:#2d0a0a; color:#f87171; border-color:#7f1d1d; }
#status.info { background:#0d1f3c; color:#f0d060; border-color:#c9a227; }
canvas { display:none; }
#start-btn { padding:12px 32px; font-size:15px; font-weight:bold; background:linear-gradient(90deg,#c9a227,#e8c547); color:#0a1628; border:none; border-radius:10px; cursor:pointer; width:100%; max-width:380px; }
#start-btn:disabled { background:#444; color:#999; cursor:not-allowed; }
</style>
</head>
<body>
<div id="container">
  <div id="video-wrap">
    <video id="video" autoplay playsinline muted></video>
    <div id="overlay">
      <div class="corner tl"></div><div class="corner tr"></div>
      <div class="corner bl"></div><div class="corner br"></div>
      <div id="scan-line"></div>
    </div>
  </div>
  <div id="status">📷 Camera start பண்ண click பண்ணுங்க</div>
  <button id="start-btn" onclick="startCamera()">📷 Camera Start</button>
  <canvas id="canvas"></canvas>
</div>
<script src="https://cdn.jsdelivr.net/npm/jsqr@1.4.0/dist/jsQR.min.js"></script>
<script>
const video=document.getElementById('video');
const canvas=document.getElementById('canvas');
const ctx=canvas.getContext('2d');
const status=document.getElementById('status');
const btn=document.getElementById('start-btn');
let scanning=false, cooldown=false;

function setStatus(msg,type){status.textContent=msg;status.className=type||"";}

function sendRoll(roll) {
  try {
    // ✅ Parent page URL மாத்தி reload — இதுவே most reliable
    const url = new URL(window.parent.location.href);
    url.searchParams.set('roll', roll);
    window.location.href = url.toString();
  } catch(e) {
    setStatus("❌ " + e.message, "error");
  }
}

function startCamera(){
  btn.disabled=true; btn.textContent="⏳ Starting...";
  navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:"environment"},width:{ideal:1280},height:{ideal:720}}})
  .then(stream=>{
    video.srcObject=stream; video.play();
    scanning=true;
    setStatus("✅ Camera ready! QR code காட்டுங்க...","info");
    btn.textContent="✅ Camera On";
    requestAnimationFrame(tick);
  })
  .catch(()=>{
    setStatus("❌ Camera Allow பண்ணுங்க!","error");
    btn.disabled=false; btn.textContent="📷 Try Again";
  });
}

function tick(){
  if(!scanning) return;
  if(video.readyState===video.HAVE_ENOUGH_DATA){
    canvas.width=video.videoWidth; canvas.height=video.videoHeight;
    ctx.drawImage(video,0,0);
    const d=ctx.getImageData(0,0,canvas.width,canvas.height);
    const code=jsQR(d.data,d.width,d.height,{inversionAttempts:"dontInvert"});
    if(code&&code.data&&!cooldown){
      cooldown=true;
      setStatus("✅ Scanned: "+code.data+" — Marking...","success");
      sendRoll(code.data);
    }
  }
  requestAnimationFrame(tick);
}
</script>
</body>
</html>"""

    components.html(scanner_html, height=500, scrolling=False)

st.markdown("---")

# ===================== TODAY SUMMARY =====================
st.markdown('<h2 id="today-summary">📋 Today Summary</h2>', unsafe_allow_html=True)
if st.button("🔴 Mark Absent for Remaining Students", use_container_width=True):
    try:
        mark_all_absent()
        get_today_summary.clear()
        st.success("✅ Absent marked!")
        st.rerun()
    except:
        st.error("⚠️ Rate limit — 1 minute பிறகு try பண்ணுங்க!")

try:
    summary = get_today_summary()
    present_list = [r for r in summary if r[3]=='Present']
    absent_list  = [r for r in summary if r[3]=='Absent']
    col_p, col_a = st.columns(2)
    with col_p:
        st.markdown(f"### ✅ Present ({len(present_list)})")
        if present_list:
            p0,p1,p2 = st.columns([2,2,2])
            p0.markdown("**Name**"); p1.markdown("**Roll No**"); p2.markdown("**Exam No**")
            st.markdown("---")
            for i,r in enumerate(present_list,1):
                pp0,pp1,pp2=st.columns([2,2,2])
                pp0.write(f"{i}. {r[0]}"); pp1.write(r[1]); pp2.write(r[2] if r[2] else "-")
        else: st.info("No present students yet!")
    with col_a:
        st.markdown(f"### ❌ Absent ({len(absent_list)})")
        if absent_list:
            a0,a1,a2 = st.columns([2,2,2])
            a0.markdown("**Name**"); a1.markdown("**Roll No**"); a2.markdown("**Exam No**")
            st.markdown("---")
            for i,r in enumerate(absent_list,1):
                aa0,aa1,aa2=st.columns([2,2,2])
                aa0.write(f"{i}. {r[0]}"); aa1.write(r[1]); aa2.write(r[2] if r[2] else "-")
        else: st.info("No absent students!")
except:
    st.warning("⚠️ 1 minute பிறகு refresh பண்ணுங்க")

st.markdown("---")

# ===================== ATTENDANCE REPORT =====================
st.markdown('<h2 id="attendance-report">📊 Attendance Report</h2>', unsafe_allow_html=True)
filter_date = st.date_input("📅 Date Select", value=date.today(), key="report_date")
if st.button("🔄 Refresh Report", use_container_width=True):
    get_report.clear()
    st.rerun()

try:
    records = get_report(filter_date)
    if records:
        present_count = sum(1 for r in records if r[4]=='Present')
        absent_count  = sum(1 for r in records if r[4]=='Absent')
        m1,m2,m3 = st.columns(3)
        m1.metric("📊 Total", len(records)); m2.metric("✅ Present", present_count); m3.metric("❌ Absent", absent_count)
        st.markdown("---")
        rep_p = [r for r in records if r[4]=='Present']
        rep_a = [r for r in records if r[4]=='Absent']
        cr1,cr2 = st.columns(2)
        with cr1:
            st.markdown(f"### ✅ Present ({len(rep_p)})")
            if rep_p:
                for i,r in enumerate(rep_p,1):
                    c1,c2,c3=st.columns([2,2,2])
                    c1.write(f"{i}. {r[0]}"); c2.write(r[1]); c3.write(r[2] if r[2] else "-")
            else: st.info("No present records!")
        with cr2:
            st.markdown(f"### ❌ Absent ({len(rep_a)})")
            if rep_a:
                for i,r in enumerate(rep_a,1):
                    c1,c2,c3=st.columns([2,2,2])
                    c1.write(f"{i}. {r[0]}"); c2.write(r[1]); c3.write(r[2] if r[2] else "-")
            else: st.info("No absent records!")
    else:
        st.info(f"📅 {filter_date} — No records!")
except:
    st.warning("⚠️ 1 minute பிறகு refresh பண்ணுங்க")
