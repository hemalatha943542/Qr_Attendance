from flask import Flask, render_template, request, jsonify, send_file
import sqlite3
import qrcode
import io
from datetime import date

app = Flask(__name__)

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

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/add_student', methods=['POST'])
def add_student():
    data = request.json
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO students (name, roll_number) VALUES (?, ?)",
                  (data['name'], data['roll_number']))
        conn.commit()
        return jsonify({'message': 'Student added successfully!'})
    except:
        return jsonify({'message': 'Roll number already exists!'})
    finally:
        conn.close()

@app.route('/students')
def get_students():
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    c.execute("SELECT * FROM students")
    students = c.fetchall()
    conn.close()
    return jsonify(students)

@app.route('/generate_qr/<roll_number>')
def generate_qr(roll_number):
    img = qrcode.make(roll_number)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')

@app.route('/mark_attendance/<roll_number>')
def mark_attendance(roll_number):
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    c.execute("SELECT id FROM students WHERE roll_number=?", (roll_number,))
    student = c.fetchone()
    if student:
        today = str(date.today())
        c.execute("SELECT * FROM attendance WHERE student_id=? AND date=?",
                  (student[0], today))
        already = c.fetchone()
        if already:
            conn.close()
            return jsonify({'message': 'Already marked today!'})
        c.execute("INSERT INTO attendance (student_id, date, status) VALUES (?, ?, ?)",
                  (student[0], today, 'Present'))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Attendance marked!'})
    conn.close()
    return jsonify({'message': 'Student not found!'})

@app.route('/attendance_report')
def attendance_report():
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    c.execute('''SELECT s.name, s.roll_number, a.date, a.status
                 FROM attendance a
                 JOIN students s ON a.student_id = s.id
                 ORDER BY a.date DESC''')
    records = c.fetchall()
    conn.close()
    return jsonify(records)
@app.route('/delete_student/<int:student_id>', methods=['DELETE'])
def delete_student(student_id):
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    c.execute("DELETE FROM students WHERE id=?", (student_id,))
    c.execute("DELETE FROM attendance WHERE student_id=?", (student_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Student deleted!'})
@app.route('/mark_absent', methods=['POST'])
def mark_absent():
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    today = str(date.today())
    c.execute("SELECT id FROM students")
    all_students = c.fetchall()
    for student in all_students:
        c.execute("SELECT * FROM attendance WHERE student_id=? AND date=?",
                  (student[0], today))
        already = c.fetchone()
        if not already:
            c.execute("INSERT INTO attendance (student_id, date, status) VALUES (?, ?, ?)",
                      (student[0], today, 'Absent'))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Absent marked for all missing students!'})


if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)