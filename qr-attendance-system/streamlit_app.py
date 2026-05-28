import streamlit as st
import sqlite3
import qrcode
import io
from datetime import date
import time

st.set_page_config(page_title="QR Attendance System", page_icon="📋", layout="wide")

st.markdown("""
<style>
.menu-btn {
    display: block;
    width: 100%;
    padding: 10px 15px;
    margin: 5px 0;
    background: #2d2d2d;
    color: white !important;
    text-decoration: none !important;
    border-radius: 8px;
    font-size: 15px;
    cursor: pointer;
    border: 1px solid #444;
}
.menu-btn:hover { background: #7c3aed; }
</style>
""", unsafe_allow_html=True)

def init_db():
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        roll_number TEXT UNIQUE NOT NULL,
        exam_number TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        date TEXT,
        status TEXT,
        FOREIGN KEY (student_id) REFERENCES students(id)
    )''')
    try:
        conn.execute('ALTER TABLE students ADD COLUMN exam_number TEXT')
    except:
        pass
    conn.commit()
    conn.close()

def add_student(name, roll, exam):
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO students (name, roll_number, exam_number) VALUES (?, ?, ?)", (name, roll, exam))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def get_students():
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    c.execute("SELECT * FROM students")
    students = c.fetchall()
    conn.close()
    return students

def delete_student(sid):
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    c.execute("DELETE FROM students WHERE id=?", (sid,))
    c.execute("DELETE FROM attendance WHERE student_id=?", (sid,))
    conn.commit()
    conn.close()

def mark_present_by_roll(roll):
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    c.execute("SELECT id, name FROM students WHERE roll_number=?", (roll,))
    student = c.fetchone()
    if student:
        today = str(date.today())
        c.execute("SELECT id, status FROM attendance WHERE student_id=? AND date=?", (student[0], today))
        existing = c.fetchone()
        if existing:
            if existing[1] == 'Absent':
                c.execute("UPDATE attendance SET status='Present' WHERE id=?", (existing[0],))
                conn.commit()
                conn.close()
                return student[1], "updated"
            else:
                conn.close()
                return student[1], "already"
        else:
            c.execute("INSERT INTO attendance (student_id, date, status) VALUES (?, ?, 'Present')",
                      (student[0], today))
            conn.commit()
            conn.close()
            return student[1], "new"
    conn.close()
    return None, ""

def mark_all_absent():
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    today = str(date.today())
    c.execute("SELECT id FROM students")
    for s in c.fetchall():
        c.execute("SELECT id FROM attendance WHERE student_id=? AND date=?", (s[0], today))
        if not c.fetchone():
            c.execute("INSERT INTO attendance (student_id, date, status) VALUES (?, ?, 'Absent')",
                      (s[0], today))
    conn.commit()
    conn.close()

def get_today_summary():
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    today = str(date.today())
    c.execute('''SELECT s.name, s.roll_number, s.exam_number, a.status
                 FROM attendance a JOIN students s ON a.student_id = s.id
                 WHERE a.date=? ORDER BY s.name''', (today,))
    records = c.fetchall()
    conn.close()
    return records

def get_report(filter_date):
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    c.execute('''SELECT s.name, s.roll_number, s.exam_number, a.date, a.status
                 FROM attendance a JOIN students s ON a.student_id = s.id
                 WHERE a.date=? ORDER BY s.name''', (str(filter_date),))
    records = c.fetchall()
    conn.close()
    return records

def generate_qr(roll):
    img = qrcode.make(roll)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf

init_db()

# Session state init
if 'last_scanned' not in st.session_state:
    st.session_state.last_scanned = ""
if 'scan_result_name' not in st.session_state:
    st.session_state.scan_result_name = ""
if 'scan_result_status' not in st.session_state:
    st.session_state.scan_result_status = ""
if 'pending_roll' not in st.session_state:
    st.session_state.pending_roll = ""

# ✅ Auto-process scanned roll from query params
query_roll = st.query_params.get("roll", "")
if query_roll and query_roll != st.session_state.last_scanned:
    st.session_state.last_scanned = query_roll
    st.session_state.pending_roll = query_roll
    name, status_val = mark_present_by_roll(query_roll)
    st.session_state.scan_result_name = name or ""
    st.session_state.scan_result_status = status_val
    st.query_params.clear()

# Sidebar
with st.sidebar:
    try:
        st.image("static/auxlogo.jpg", width=120)
    except:
        st.write("📋")
    st.title("QR Attendance")
    st.markdown("---")
    st.markdown("""
    <a class="menu-btn" href="#add-student">➕ Add Student</a>
    <a class="menu-btn" href="#students-list">👥 Students List</a>
    <a class="menu-btn" href="#qr-scanner">📷 QR Scanner</a>
    <a class="menu-btn" href="#today-summary">📋 Today Summary</a>
    <a class="menu-btn" href="#attendance-report">📊 Attendance Report</a>
    """, unsafe_allow_html=True)
    st.markdown("---")
    st.markdown(f"📅 Today: **{date.today()}**")

st.title("📋 QR Attendance System")
st.markdown("---")

# ➕ ADD STUDENT
st.markdown('<h2 id="add-student">➕ Add Student</h2>', unsafe_allow_html=True)
col1, col2, col3 = st.columns(3)
with col1:
    name = st.text_input("Student Name")
with col2:
    roll = st.text_input("Roll Number")
with col3:
    exam = st.text_input("Exam Number")

if st.button("➕ Add Student & Generate QR", use_container_width=True):
    if name and roll:
        if add_student(name, roll, exam):
            st.success(f"✅ {name} added!")
            st.image(generate_qr(roll), caption=f"QR - {name}", width=200)
        else:
            st.error("❌ Roll number already exists!")
    else:
        st.warning("⚠️ Name மற்றும் Roll Number போடுங்க!")

st.markdown("---")

# 👥 STUDENTS LIST
st.markdown('<h2 id="students-list">👥 Students List</h2>', unsafe_allow_html=True)
students = get_students()
if students:
    h0,h1,h2,h3,h4,h5 = st.columns([1,2,2,2,2,1])
    h0.markdown("**S.No**")
    h1.markdown("**Name**")
    h2.markdown("**Roll Number**")
    h3.markdown("**Exam Number**")
    h4.markdown("**QR Code**")
    h5.markdown("**Delete**")
    st.markdown("---")
    for i, s in enumerate(students, 1):
        c0,c1,c2,c3,c4,c5 = st.columns([1,2,2,2,2,1])
        c0.write(i)
        c1.write(s[1])
        c2.write(s[2])
        c3.write(s[3] if len(s) > 3 and s[3] else "-")
        with c4:
            st.image(generate_qr(s[2]), width=80)
        with c5:
            if st.button("🗑️", key=f"d{s[0]}"):
                delete_student(s[0])
                st.rerun()
else:
    st.info("No students yet!")

st.markdown("---")

# 📷 QR SCANNER
st.markdown('<h2 id="qr-scanner">📷 QR Scanner</h2>', unsafe_allow_html=True)
st.info("📱 QR code scan பண்ணினா மட்டும் Present mark ஆகும்!")

# Show scan result
if st.session_state.scan_result_name:
    n = st.session_state.scan_result_name
    s = st.session_state.scan_result_status
    if s == "updated":
        st.success(f"✅ {n} — Absent → Present Marked!")
    elif s == "already":
        st.info(f"ℹ️ {n} — Already Present!")
    elif s == "new":
        st.success(f"✅ {n} — Present Marked!")
    else:
        st.error(f"❌ Student not found!")

# Get current page URL for scanner to use
scanner_html = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: #0f0f0f; font-family: Arial, sans-serif; }
  #container {
    display: flex; flex-direction: column;
    align-items: center; padding: 16px; gap: 12px;
  }
  #video-wrap {
    position: relative; width: 100%; max-width: 380px;
    border-radius: 16px; overflow: hidden;
    border: 2px solid #7c3aed;
    box-shadow: 0 0 20px rgba(124,58,237,0.4);
  }
  video { width: 100%; display: block; border-radius: 14px; }
  #overlay {
    position: absolute; top: 50%; left: 50%;
    transform: translate(-50%, -50%);
    width: 180px; height: 180px;
    border: 3px solid #7c3aed; border-radius: 12px;
    box-shadow: 0 0 0 9999px rgba(0,0,0,0.35);
    pointer-events: none;
  }
  .corner { position: absolute; width: 22px; height: 22px; border-color: #a78bfa; border-style: solid; }
  .tl { top:-2px; left:-2px; border-width:3px 0 0 3px; border-radius:4px 0 0 0; }
  .tr { top:-2px; right:-2px; border-width:3px 3px 0 0; border-radius:0 4px 0 0; }
  .bl { bottom:-2px; left:-2px; border-width:0 0 3px 3px; border-radius:0 0 0 4px; }
  .br { bottom:-2px; right:-2px; border-width:0 3px 3px 0; border-radius:0 0 4px 0; }
  #scan-line {
    position: absolute; left: 4px; right: 4px; height: 2px;
    background: linear-gradient(90deg, transparent, #a78bfa, transparent);
    animation: scan 2s linear infinite; top: 10%;
  }
  @keyframes scan { 0%{top:10%} 50%{top:85%} 100%{top:10%} }
  #status {
    width:100%; max-width:380px; padding:12px 16px;
    border-radius:10px; font-size:15px; text-align:center;
    font-weight:bold; background:#1e1e1e; color:#ccc;
    border:1px solid #333; min-height:48px;
  }
  #status.success { background:#052e16; color:#4ade80; border-color:#166534; }
  #status.error   { background:#2d0a0a; color:#f87171; border-color:#7f1d1d; }
  #status.info    { background:#0c1a2e; color:#60a5fa; border-color:#1e3a5f; }
  canvas { display:none; }
  #start-btn {
    padding:12px 32px; font-size:15px; font-weight:bold;
    background:#7c3aed; color:white; border:none;
    border-radius:10px; cursor:pointer;
    width:100%; max-width:380px;
  }
  #start-btn:hover { background:#6d28d9; }
  #start-btn:disabled { background:#444; cursor:not-allowed; }
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
  <div id="status">📷 Camera start பண்ண கீழே click பண்ணுங்க</div>
  <button id="start-btn" onclick="startCamera()">📷 Camera Start</button>
  <canvas id="canvas"></canvas>
</div>

<script src="https://cdn.jsdelivr.net/npm/jsqr@1.4.0/dist/jsQR.min.js"></script>
<script>
const video  = document.getElementById('video');
const canvas = document.getElementById('canvas');
const ctx    = canvas.getContext('2d');
const status = document.getElementById('status');
const btn    = document.getElementById('start-btn');

let lastScanned = "";
let scanning    = false;
let cooldown    = false;

function setStatus(msg, type) {
  status.textContent = msg;
  status.className   = type || "";
}

function startCamera() {
  btn.disabled    = true;
  btn.textContent = "⏳ Starting...";
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    setStatus("❌ Browser camera support இல்ல! Chrome use பண்ணுங்க.", "error");
    btn.disabled = false; return;
  }
  navigator.mediaDevices.getUserMedia({
    video: { facingMode: { ideal: "environment" }, width: { ideal: 1280 }, height: { ideal: 720 } }
  })
  .then(stream => {
    video.srcObject = stream;
    video.play();
    scanning = true;
    setStatus("✅ Camera ready! QR code காட்டுங்க...", "info");
    btn.textContent = "✅ Camera On";
    requestAnimationFrame(tick);
  })
  .catch(err => {
    setStatus("❌ Camera access Allow பண்ணுங்க!", "error");
    btn.disabled    = false;
    btn.textContent = "📷 Try Again";
  });
}

function tick() {
  if (!scanning) return;
  if (video.readyState === video.HAVE_ENOUGH_DATA) {
    canvas.width  = video.videoWidth;
    canvas.height = video.videoHeight;
    ctx.drawImage(video, 0, 0);
    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const code = jsQR(imageData.data, imageData.width, imageData.height, {
      inversionAttempts: "dontInvert"
    });
    if (code && code.data && !cooldown) {
      cooldown = true;
      setStatus("⏳ Marking present: " + code.data + "...", "info");

      // ✅ KEY FIX: parent window URL-ல roll param சேர்த்து reload பண்ணு
     const parentUrl = window.top.location.href.split('?')[0];
window.top.location.href = parentUrl + "?roll=" + encodeURIComponent(code.data);
    }
  }
  requestAnimationFrame(tick);
}
</script>
</body>
</html>
"""

import streamlit.components.v1 as components
st.markdown('<h2 id="qr-scanner">📷 QR Scanner</h2>', unsafe_allow_html=True)
st.info("📱 QR code scan பண்ணினா மட்டும் Present mark ஆகும்!")
components.html(scanner_html, height=650)
# Show scan result
if st.session_state.scan_result_name:
    n = st.session_state.scan_result_name
    s = st.session_state.scan_result_status
    if s == "updated":
        st.success(f"✅ {n} — Absent → Present Marked!")
    elif s == "already":
        st.info(f"ℹ️ {n} — Already Present!")
    elif s == "new":
        st.success(f"✅ {n} — Present Marked!")
    else:
        st.error(f"❌ Student not found!")
st.markdown("---")

# 📋 TODAY SUMMARY
st.markdown('<h2 id="today-summary">📋 Today Summary</h2>', unsafe_allow_html=True)

if st.button("🔴 Mark Absent for Remaining Students", use_container_width=True):
    mark_all_absent()
    st.success("✅ Absent marked!")
    st.rerun()

summary = get_today_summary()
present_list = [r for r in summary if r[3] == 'Present']
absent_list  = [r for r in summary if r[3] == 'Absent']

col_p, col_a = st.columns(2)

with col_p:
    st.markdown(f"### ✅ Present ({len(present_list)})")
    if present_list:
        p0,p1,p2 = st.columns([2,2,2])
        p0.markdown("**Name**")
        p1.markdown("**Roll No**")
        p2.markdown("**Exam No**")
        st.markdown("---")
        for i, r in enumerate(present_list, 1):
            pp0,pp1,pp2 = st.columns([2,2,2])
            pp0.write(f"{i}. {r[0]}")
            pp1.write(r[1])
            pp2.write(r[2] if r[2] else "-")
    else:
        st.info("No present students yet!")

with col_a:
    st.markdown(f"### ❌ Absent ({len(absent_list)})")
    if absent_list:
        a0,a1,a2 = st.columns([2,2,2])
        a0.markdown("**Name**")
        a1.markdown("**Roll No**")
        a2.markdown("**Exam No**")
        st.markdown("---")
        for i, r in enumerate(absent_list, 1):
            aa0,aa1,aa2 = st.columns([2,2,2])
            aa0.write(f"{i}. {r[0]}")
            aa1.write(r[1])
            aa2.write(r[2] if r[2] else "-")
    else:
        st.info("No absent students!")

st.markdown("---")

# 📊 ATTENDANCE REPORT
st.markdown('<h2 id="attendance-report">📊 Attendance Report</h2>', unsafe_allow_html=True)

filter_date = st.date_input("📅 Date Select பண்ணுங்க", value=date.today())

if st.button("🔄 Refresh Report", use_container_width=True):
    st.rerun()

records = get_report(filter_date)

if records:
    present_count = sum(1 for r in records if r[4] == 'Present')
    absent_count  = sum(1 for r in records if r[4] == 'Absent')

    m1, m2, m3 = st.columns(3)
    m1.metric("📊 Total", len(records))
    m2.metric("✅ Present", present_count)
    m3.metric("❌ Absent", absent_count)

    st.markdown("---")

    rep_present = [r for r in records if r[4] == 'Present']
    rep_absent  = [r for r in records if r[4] == 'Absent']

    col_rp, col_ra = st.columns(2)

    with col_rp:
        st.markdown(f"### ✅ Present List ({len(rep_present)})")
        if rep_present:
            rp0,rp1,rp2 = st.columns([2,2,2])
            rp0.markdown("**Name**")
            rp1.markdown("**Roll No**")
            rp2.markdown("**Exam No**")
            st.markdown("---")
            for i, r in enumerate(rep_present, 1):
                rpp0,rpp1,rpp2 = st.columns([2,2,2])
                rpp0.write(f"{i}. {r[0]}")
                rpp1.write(r[1])
                rpp2.write(r[2] if r[2] else "-")
        else:
            st.info("No present records!")

    with col_ra:
        st.markdown(f"### ❌ Absent List ({len(rep_absent)})")
        if rep_absent:
            ra0,ra1,ra2 = st.columns([2,2,2])
            ra0.markdown("**Name**")
            ra1.markdown("**Roll No**")
            ra2.markdown("**Exam No**")
            st.markdown("---")
            for i, r in enumerate(rep_absent, 1):
                raa0,raa1,raa2 = st.columns([2,2,2])
                raa0.write(f"{i}. {r[0]}")
                raa1.write(r[1])
                raa2.write(r[2] if r[2] else "-")
        else:
            st.info("No absent records!")
else:
    st.info(f"📅 {filter_date} — No records!")