import streamlit as st
import sqlite3
import qrcode
import io
from datetime import date
import cv2
import numpy as np
from pyzbar import pyzbar
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, RTCConfiguration

st.set_page_config(page_title="QR Attendance System", page_icon="📋", layout="wide")

def init_db():
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        roll_number TEXT UNIQUE NOT NULL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        date TEXT,
        status TEXT,
        FOREIGN KEY (student_id) REFERENCES students(id)
    )''')
    conn.commit()
    conn.close()

def add_student(name, roll):
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO students (name, roll_number) VALUES (?, ?)", (name, roll))
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

def mark_present(roll):
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    c.execute("SELECT id, name FROM students WHERE roll_number=?", (roll,))
    student = c.fetchone()
    if student:
        today = str(date.today())
        c.execute("SELECT * FROM attendance WHERE student_id=? AND date=?", (student[0], today))
        if c.fetchone():
            conn.close()
            return "already", student[1]
        c.execute("INSERT INTO attendance (student_id, date, status) VALUES (?, ?, ?)",
                  (student[0], today, 'Present'))
        conn.commit()
        conn.close()
        return "success", student[1]
    conn.close()
    return "notfound", ""

def mark_absent_all():
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    today = str(date.today())
    c.execute("SELECT id FROM students")
    for s in c.fetchall():
        c.execute("SELECT * FROM attendance WHERE student_id=? AND date=?", (s[0], today))
        if not c.fetchone():
            c.execute("INSERT INTO attendance (student_id, date, status) VALUES (?, ?, ?)",
                      (s[0], today, 'Absent'))
    conn.commit()
    conn.close()

def get_report():
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    c.execute('''SELECT s.name, s.roll_number, a.date, a.status
                 FROM attendance a JOIN students s ON a.student_id = s.id
                 ORDER BY a.date DESC''')
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
    st.markdown("➕ Add Student")
    st.markdown("👥 Students List")
    st.markdown("📷 QR Scanner")
    st.markdown("📊 Attendance Report")
    st.markdown("---")
    st.markdown(f"📅 Today: **{date.today()}**")

# Title
st.title("📋 QR Attendance System")
st.markdown("---")

# ➕ ADD STUDENT
st.markdown("## ➕ Add Student")
col1, col2 = st.columns(2)
with col1:
    name = st.text_input("Student Name")
with col2:
    roll = st.text_input("Roll Number")
if st.button("➕ Add Student & Generate QR", use_container_width=True):
    if name and roll:
        if add_student(name, roll):
            st.success(f"✅ {name} added!")
            st.image(generate_qr(roll), caption=f"QR - {name}", width=200)
        else:
            st.error("❌ Roll number already exists!")
    else:
        st.warning("⚠️ Name மற்றும் Roll Number போடுங்க!")

st.markdown("---")

# 👥 STUDENTS LIST
st.markdown("## 👥 Students List")
students = get_students()
if students:
    h0,h1,h2,h3,h4,h5 = st.columns([1,2,2,2,2,2])
    h0.markdown("**ID**")
    h1.markdown("**Name**")
    h2.markdown("**Roll No**")
    h3.markdown("**QR Code**")
    h4.markdown("**Present**")
    h5.markdown("**Delete**")
    st.markdown("---")
    for s in students:
        c0,c1,c2,c3,c4,c5 = st.columns([1,2,2,2,2,2])
        c0.write(s[0])
        c1.write(s[1])
        c2.write(s[2])
        with c3:
            st.image(generate_qr(s[2]), width=80)
        with c4:
            if st.button("✅ Present", key=f"p{s[0]}"):
                result, sname = mark_present(s[2])
                if result == "success":
                    st.success(f"✅ Marked!")
                elif result == "already":
                    st.warning("Already marked!")
        with c5:
            if st.button("🗑️", key=f"d{s[0]}"):
                delete_student(s[0])
                st.rerun()
else:
    st.info("No students yet!")

st.markdown("---")

# 📷 QR SCANNER
st.markdown("## 📷 QR Scanner")
st.info("Camera-ல QR code காட்டுங்க — Attendance automatic-ஆ mark ஆகும்! 📱")

if 'last_scanned' not in st.session_state:
    st.session_state.last_scanned = ""
if 'scan_message' not in st.session_state:
    st.session_state.scan_message = ""

class QRScanner(VideoProcessorBase):
    def __init__(self):
        self.qr_data = None

    def transform(self, frame):
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
        return img

RTC_CONFIG = RTCConfiguration({"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]})

ctx = webrtc_streamer(
    key="qr-scanner",
    video_processor_factory=QRScanner,
    rtc_configuration=RTC_CONFIG,
    media_stream_constraints={"video": True, "audio": False}
)

scan_placeholder = st.empty()

if ctx.video_processor:
    scanned_roll = ctx.video_processor.qr_data
    if scanned_roll != st.session_state.last_scanned:
        st.session_state.last_scanned = scanned_roll
        result, sname = mark_present(scanned_roll)
        if result == "success":
            scan_placeholder.success(f"✅ {sname} ({scanned_roll}) — Present Marked!")
        elif result == "already":
            scan_placeholder.warning(f"⚠️ {sname} ({scanned_roll}) — Already marked today!")
        else:
            scan_placeholder.error(f"❌ Student not found: {scanned_roll}")

st.markdown("---")

# 📊 ATTENDANCE REPORT
st.markdown("## 📊 Attendance Report")
col_a, col_b = st.columns(2)
with col_a:
    if st.button("🔴 Mark Absent for Today", use_container_width=True):
        mark_absent_all()
        st.success("✅ Absent marked!")
with col_b:
    if st.button("🔄 Refresh Report", use_container_width=True):
        st.rerun()

records = get_report()
if records:
    r0,r1,r2,r3 = st.columns([2,2,2,2])
    r0.markdown("**Name**")
    r1.markdown("**Roll No**")
    r2.markdown("**Date**")
    r3.markdown("**Status**")
    st.markdown("---")
    for r in records:
        rc0,rc1,rc2,rc3 = st.columns([2,2,2,2])
        rc0.write(r[0])
        rc1.write(r[1])
        rc2.write(r[2])
        if r[3] == 'Present':
            rc3.success("✅ Present")
        else:
            rc3.error("❌ Absent")
else:
    st.info("No records yet!")