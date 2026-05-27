import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
conn = sqlite3.connect(BASE_DIR / "database.db")
c = conn.cursor()

# -------- TABLES --------
c.execute("""

CREATE TABLE IF NOT EXISTS students (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    username TEXT,

    password TEXT,

    name TEXT,

    enrollment TEXT,

    dept TEXT,

    semester TEXT,

    year TEXT,

    degree TEXT,

    passing_year TEXT,

    attendance FLOAT DEFAULT 0

)

""")

c.execute("""
CREATE TABLE IF NOT EXISTS subjects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT,
    name TEXT,
    dept TEXT,
    semester TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS units (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id INTEGER,
    name TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    unit_id INTEGER,
    title TEXT
)
""")

# -------- FACULTY TABLE (IMPORTANT: UPAR HI BANEGI) --------
c.execute("""
CREATE TABLE IF NOT EXISTS faculty (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    faculty_id TEXT,
    password TEXT,
    name TEXT
)
""")

# -------- ADD FACULTY PROFILE COLUMNS --------
try:
    c.execute("ALTER TABLE faculty ADD COLUMN email TEXT")
except:
    pass

try:
    c.execute("ALTER TABLE faculty ADD COLUMN department TEXT")
except:
    pass

try:
    c.execute("ALTER TABLE faculty ADD COLUMN phone TEXT")
except:
    pass

# -------- SUBMISSIONS TABLE --------
c.execute("""
CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    assignment_id INTEGER,
    student_id INTEGER,

    file_path TEXT,

    ai_status TEXT DEFAULT 'pending',
    status TEXT DEFAULT 'pending',

    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
# -------- ADD ATTENDANCE COLUMN SAFELY --------

try:

    c.execute("""

        ALTER TABLE students
        ADD COLUMN attendance FLOAT DEFAULT 0

    """)

except:
    pass

# -------- ADD EXTRA COLUMNS SAFELY --------
try:
    c.execute("ALTER TABLE subjects ADD COLUMN faculty_id INTEGER")
except:
    pass

try:
    c.execute("ALTER TABLE assignments ADD COLUMN file_path TEXT")
except:
    pass


# -------- STUDENTS (SAFE INSERT) --------
# if c.execute("SELECT COUNT(*) FROM students").fetchone()[0] == 0:
#     c.execute("""
#     INSERT INTO students 
#     (username, password, name, enrollment, dept, semester, year, degree, passing_year)
#     VALUES 
#     ('0187CY231001','1234','Student 1','0187CY231001','CSE','4','2nd Year','B.Tech','2026')
#     """)

# -------- SUBJECTS (SAFE INSERT) --------
# -------- SUBJECTS RESET + INSERT --------
c.execute("DELETE FROM subjects")

subjects = [
    ("CY601", "CCID", "CSE - Cyber Security", "6th SEM"),
    ("CY602", "SE", "CSE - Cyber Security", "6th SEM"),
    ("CY603(A)", "IWT", "CSE - Cyber Security", "6th SEM"),
    ("CY604(B)", "OOAD", "CSE - Cyber Security", "6th SEM")
]

c.executemany(
    "INSERT INTO subjects (code, name, dept, semester) VALUES (?, ?, ?, ?)",
    subjects
)
# -------- MULTIPLE FACULTY (SAFE INSERT) --------
c.executemany("""
INSERT OR IGNORE INTO faculty (id, faculty_id, password, name, email, department, phone)
VALUES (?, ?, ?, ?, ?, ?, ?)
""", [
    (1, 'F101', '1234', 'Yogesh Sir', 'yogesh@gmail.com', 'Cyber Security', '9999999991'),
    (2, 'F102', '1234', 'Garima Maam', 'garima@gmail.com', 'Cyber Security', '9999999992'),
    (3, 'F103', '1234', 'Abdulla Sir', 'abdulla@gmail.com', 'Cyber Security', '9999999993'),
    (4, 'F104', '1234', 'Shivani Maam', 'shivani@gmail.com', 'Cyber Security', '9999999994')
])

#-------- SUBJECT → FACULTY LINK --------
c.execute("UPDATE subjects SET faculty_id = 1 WHERE name = 'CCID'")
c.execute("UPDATE subjects SET faculty_id = 2 WHERE name = 'SE'")
c.execute("UPDATE subjects SET faculty_id = 3 WHERE name = 'IWT'")
c.execute("UPDATE subjects SET faculty_id = 4 WHERE name = 'OOAD'")


# -------- UNITS (SAFE INSERT) --------
# -------- UNITS (CORRECT LINKING) --------
c.execute("DELETE FROM units")

subjects_db = c.execute("SELECT id FROM subjects").fetchall()

units = []
for sub in subjects_db:
    subject_id = sub[0]
    for i in range(1, 6):
        units.append((subject_id, f"Unit {i}"))

c.executemany(
    "INSERT INTO units (subject_id, name) VALUES (?, ?)",
    units
)

import csv

data = []

with open(BASE_DIR / "students.csv", newline='', encoding='utf-8') as file:
    reader = csv.reader(file)

    for row in reader:
        roll = row[0]
        name = row[1]

        data.append((
            roll,                      # username
            "1234",                   # password
            name,                     # name
            roll,                     # enrollment
            "CSE - Cyber Security",   # ✅ FIXED BRANCH
            "6th SEM",                # ✅ FIXED SEM
            "3rd Year",               # ✅ FIXED YEAR
            "B.Tech",
            "2027"                    # ✅ FIXED PASSING YEAR
        ))
c.executemany("""
INSERT OR REPLACE INTO students
(username, password, name, enrollment, dept, semester, year, degree, passing_year)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
""", data)

conn.commit()
conn.close()

print("Database fully initialized.")
