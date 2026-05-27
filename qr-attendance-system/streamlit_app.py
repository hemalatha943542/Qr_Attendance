import streamlit as st
import sqlite3
import qrcode
import io
from datetime import date

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

def mark_present_by_scan(roll):
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

if 'last_scanned' not in st.session_state:
    st.session_state.last_scanned = ""

try:
    from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, RTCConfiguration
    import cv2
    import numpy as np
    from pyzbar import pyzbar
    import av

    class QRScanner(VideoProcessorBase):
        def __init__(self):
            self.qr_data = None

        def recv(self, frame):
            img = frame.to_ndarray(format="bgr24")
            decoded = pyzbar.decode(img)
            for obj in decoded:
                qr_text = obj.data.decode('utf-8')
                self.qr_data = qr_text
                pts = np.array([[obj.polygon[i].x, obj.polygon[i].y]
                               for i in range(len(obj.polygon))], np.int32)
                cv2.polylines(img, [pts], True, (0, 255, 0), 3)
                cv2.putText(img, qr_text,
                           (obj.rect.left, obj.rect.top - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            return av.VideoFrame.from_ndarray(img, format="bgr24")

    RTC_CONFIG = RTCConfiguration({"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]})
    ctx = webrtc_streamer(
        key="qr-scanner",
        video_processor_factory=QRScanner,
        rtc_configuration=RTC_CONFIG,
        media_stream_constraints={"video": True, "audio": False}
    )

    scan_placeholder = st.empty()
    if ctx.video_processor:
        if hasattr(ctx.video_processor, 'qr_data') and ctx.video_processor.qr_data:
            scanned_roll = ctx.video_processor.qr_data
            if scanned_roll != st.session_state.last_scanned:
                st.session_state.last_scanned = scanned_roll
                student_name, status = mark_present_by_scan(scanned_roll)
                if student_name:
                    if status == "updated":
                        scan_placeholder.success(f"✅ {student_name} — Absent → Present Marked!")
                    elif status == "already":
                        scan_placeholder.info(f"ℹ️ {student_name} — Already Present!")
                    else:
                        scan_placeholder.success(f"✅ {student_name} — Present Marked!")
                else:
                    scan_placeholder.error(f"❌ Student not found: {scanned_roll}")
except Exception as e:
    st.warning("Scanner load ஆகல!")

st.markdown("---")

# 📋 TODAY SUMMARY
st.markdown('<h2 id="today-summary">📋 Today Summary</h2>', unsafe_allow_html=True)

if st.button("🔴 Mark Absent for Remaining Students", use_container_width=True):
    mark_all_absent()
    st.success("✅ Absent marked!")
    st.rerun()

summary = get_today_summary()
present_list = [r for r in summary if r[3] == 'Present']
absent_list = [r for r in summary if r[3] == 'Absent']

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
    absent_count = sum(1 for r in records if r[4] == 'Absent')

    m1, m2, m3 = st.columns(3)
    m1.metric("📊 Total", len(records))
    m2.metric("✅ Present", present_count)
    m3.metric("❌ Absent", absent_count)

    st.markdown("---")

    rep_present = [r for r in records if r[4] == 'Present']
    rep_absent = [r for r in records if r[4] == 'Absent']

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