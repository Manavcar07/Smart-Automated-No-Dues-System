from flask import Flask, render_template, request, redirect, session , flash , url_for
from AI.evaluator import evaluate_assignment
import sqlite3
import webbrowser
import os
from flask import send_from_directory
import time

app = Flask(__name__)
app.secret_key = "secret123"

UPLOAD_FOLDER = os.path.join(app.root_path, "uploads")
DB_PATH = os.path.join(app.root_path, "database.db")

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
# -------- AI CHECK FUNCTION --------
def ai_check(file_path):
    try:
        with open(file_path, "r", errors="ignore") as f:
            text = f.read().lower()

        # simple logic (tu baad me improve karega)
        if len(text) > 100 and ("introduction" in text or "conclusion" in text):
            return "approved"
        else:
            return "rejected"

    except:
        return "rejected"


# -------- DB --------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def home():
    return redirect('/login')


# -------- LOGIN --------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        # 🔹 Student Login
        c.execute("SELECT * FROM students WHERE username=? AND password=?", (username, password))
        student = c.fetchone()

        if student:
            session['user_id'] = student[0]
            session['role'] = 'student'
            conn.close()
            return redirect('/dashboard')

        # 🔹 Faculty Login (FIXED)
        c.execute("SELECT * FROM faculty WHERE faculty_id=? AND password=?", (username, password))
        faculty = c.fetchone()

        if faculty:
            session['faculty_id'] = faculty[0]  # 🔥 IMPORTANT FIX
            session['role'] = 'faculty'
            conn.close()
            return redirect('/faculty_dashboard')

        conn.close()
        return "<h3>Invalid Login ❌</h3>"

    return render_template('auth/login.html')

# -------- DASHBOARD --------
@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect("/")

    conn = get_db()

    user = conn.execute("""
        SELECT *
        FROM students
        WHERE id=?
    """, (session["user_id"],)).fetchone()

    attendance = user["attendance"] if "attendance" in user.keys() else 0

    notifications = conn.execute("""
        SELECT *
        FROM notifications
        WHERE student_id=?
        ORDER BY id DESC
        LIMIT 10
    """, (session["user_id"],)).fetchall()

    notification_count = conn.execute("""
        SELECT COUNT(*)
        FROM notifications
        WHERE student_id=?
        AND is_read=0
    """, (session["user_id"],)).fetchone()[0]

    subjects = conn.execute("""
        SELECT id, name
        FROM subjects
        WHERE dept=? AND semester=?
    """, (
        user["dept"],
        user["semester"]
    )).fetchall()

    subjects_with_status = []

    for s in subjects:

        total_sub = conn.execute("""
            SELECT COUNT(*)
            FROM assignments a
            JOIN units u ON a.unit_id = u.id
            WHERE u.subject_id=?
        """, (s["id"],)).fetchone()[0]

        approved_sub = conn.execute("""
            SELECT COUNT(DISTINCT sub.assignment_id)
            FROM submissions sub
            JOIN assignments a ON sub.assignment_id = a.id
            JOIN units u ON a.unit_id = u.id
            WHERE sub.student_id=?
            AND sub.status='approved'
            AND u.subject_id=?
        """, (
            session["user_id"],
            s["id"]
        )).fetchone()[0]

        submitted_sub = conn.execute("""
            SELECT COUNT(DISTINCT sub.assignment_id)
            FROM submissions sub
            JOIN assignments a ON sub.assignment_id = a.id
            JOIN units u ON a.unit_id = u.id
            WHERE sub.student_id=?
            AND u.subject_id=?
        """, (
            session["user_id"],
            s["id"]
        )).fetchone()[0]

        if total_sub > 0 and approved_sub == total_sub:

            status = "Cleared"
            remark = "All Assignments Approved"

        elif submitted_sub > 0:

            status = "Pending"
            remaining = max(0, total_sub - approved_sub)
            remark = f"{remaining} Assignment Pending"

        else:

            status = "Pending"
            remark = "No Assignment Submitted"

        subjects_with_status.append({
            "id": s["id"],
            "name": s["name"],
            "status": status,
            "remark": remark,
            "submitted": submitted_sub,
            "approved": approved_sub,
            "total": total_sub
        })

    # TOTAL APPROVED
    approved = conn.execute("""
        SELECT COUNT(DISTINCT sub.assignment_id)
        FROM submissions sub
        JOIN assignments a ON sub.assignment_id = a.id
        JOIN units u ON a.unit_id = u.id
        JOIN subjects s ON u.subject_id = s.id
        WHERE sub.student_id=?
        AND sub.status='approved'
        AND s.dept=?
        AND s.semester=?
    """, (
        session["user_id"],
        user["dept"],
        user["semester"]
    )).fetchone()[0]

    # TOTAL ASSIGNMENTS
    total_assignments = conn.execute("""
        SELECT COUNT(*)
        FROM assignments a
        JOIN units u ON a.unit_id = u.id
        JOIN subjects s ON u.subject_id = s.id
        WHERE s.dept=?
        AND s.semester=?
    """, (
        user["dept"],
        user["semester"]
    )).fetchone()[0]

    pending = max(0, total_assignments - approved)

    if total_assignments > 0:
        progress = min(
            100,
            round((approved / total_assignments) * 100)
        )
    else:
        progress = 0

    if progress < 100:

        no_dues_status = "Locked"
        no_dues_message = f"{pending} Assignments Remaining"

    elif attendance < 75:

        no_dues_status = "Locked"
        no_dues_message = (
            f"Attendance Shortage ({attendance}%). "
            "Minimum 75% Required"
        )

    else:

        no_dues_status = "Unlocked"
        no_dues_message = "Eligible For No Dues"

    conn.close()

    return render_template(
        "student/student.html",
        user=user,
        approved=approved,
        pending=pending,
        progress=progress,
        attendance=attendance,
        no_dues_status=no_dues_status,
        no_dues_message=no_dues_message,
        subjects=subjects_with_status,
        notifications=notifications,
        notification_count=notification_count
    )
    
# -------- FACULTY DASHBOARD --------
@app.route("/faculty_dashboard")
def faculty_dashboard():

    if "faculty_id" not in session:
        return redirect("/")

    conn = get_db()

    # Current Faculty
    faculty = conn.execute("""
        SELECT *
        FROM faculty
        WHERE id=?
    """, (session["faculty_id"],)).fetchone()

    # Faculty Subjects
    subjects = conn.execute("""
        SELECT *
        FROM subjects
        WHERE faculty_id=?
    """, (session["faculty_id"],)).fetchall()

    # Faculty Units
    units = conn.execute("""
        SELECT u.*
        FROM units u
        JOIN subjects s
        ON u.subject_id = s.id
        WHERE s.faculty_id=?
    """, (session["faculty_id"],)).fetchall()

    # Total Assignments
    total_assignments = conn.execute("""
        SELECT COUNT(a.id)
        FROM assignments a
        JOIN units u ON a.unit_id=u.id
        JOIN subjects s ON u.subject_id=s.id
        WHERE s.faculty_id=?
    """, (session["faculty_id"],)).fetchone()[0]

    # Pending Reviews Count
    pending_count = conn.execute("""
        SELECT COUNT(sub.id)
        FROM submissions sub
        JOIN assignments a ON sub.assignment_id=a.id
        JOIN units u ON a.unit_id=u.id
        JOIN subjects s ON u.subject_id=s.id
        WHERE s.faculty_id=?
        AND sub.status='pending'
    """, (session["faculty_id"],)).fetchone()[0]

    conn.close()

    return render_template(
        "faculty/faculty_dashboard.html",
        faculty=faculty,
        subjects=subjects,
        units=units,
        total_assignments=total_assignments,
        pending_count=pending_count
    )
#-------- PENDING REVIEWS --------    
@app.route("/pending_reviews")
def pending_reviews():

    if "faculty_id" not in session:
        return redirect("/")

    conn = get_db()

    assignments = conn.execute("""
        SELECT DISTINCT
            a.id,
            a.title,
            u.name AS unit_name,
            s.name AS subject_name
        FROM submissions sub
        JOIN assignments a ON sub.assignment_id = a.id
        JOIN units u ON a.unit_id = u.id
        JOIN subjects s ON u.subject_id = s.id
        WHERE s.faculty_id = ?
        AND LOWER(sub.status)='pending'
    """, (session["faculty_id"],)).fetchall()

    conn.close()

    return render_template(
        "faculty/pending_reviews.html",
        assignments=assignments
    )
#-------- SERVE UPLOADED FILES --------
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# -------- SUBJECTS --------
@app.route("/subjects")
def subjects():
    if "user_id" not in session:
        return redirect("/")

    conn = get_db()

    user = conn.execute(
        "SELECT * FROM students WHERE id=?",
        (session["user_id"],)
    ).fetchone()

    subjects = conn.execute(
        "SELECT * FROM subjects WHERE dept=? AND semester=?",
        (user["dept"], user["semester"])
    ).fetchall()

    return render_template("student/subjects.html", subjects=subjects)


# -------- UNITS --------
@app.route("/units/<int:subject_id>")
def units(subject_id):
    if "user_id" not in session:
        return redirect("/")

    conn = get_db()

    units = conn.execute(
        "SELECT * FROM units WHERE subject_id=?",
        (subject_id,)
    ).fetchall()

    return render_template("student/units.html", units=units)

# -------- ASSIGNMENTS --------
@app.route("/assignments/<int:unit_id>")
def assignments(unit_id):

    if "user_id" not in session:
        return redirect("/")

    conn = get_db()

    # ✅ GET ASSIGNMENTS
    assignments = conn.execute("""
        SELECT * FROM assignments
        WHERE unit_id=?
    """, (unit_id,)).fetchall()

    updated_assignments = []

    # ✅ CHECK SUBMISSION STATUS
    for a in assignments:

        submission = conn.execute("""
            SELECT * FROM submissions
            WHERE assignment_id=?
            AND student_id=?
            ORDER BY id DESC
            LIMIT 1
        """, (
            a["id"],
            session["user_id"]
        )).fetchone()

        assignment_data = dict(a)

        # ✅ STATUS LOGIC
        if submission:

            assignment_data["submission_status"] = submission["status"]

            assignment_data["submission_id"] = submission["id"]

            assignment_data["submitted_file"] = submission["file_path"]

        else:

            assignment_data["submission_status"] = "not_submitted"

            assignment_data["submission_id"] = None

            assignment_data["submitted_file"] = None

        updated_assignments.append(assignment_data)

    # ✅ GET SUBJECT ID
    row = conn.execute("""
        SELECT subject_id FROM units
        WHERE id=?
    """, (unit_id,)).fetchone()

    subject_id = row[0] if row else 0

    conn.close()

    # ✅ RENDER PAGE
    return render_template(
        "student/assignments.html",
        assignments=updated_assignments,
        unit_id=unit_id,
        subject_id=subject_id
    )
# -------- Upload --------
@app.route("/upload", methods=["POST"])
def upload():

    if "user_id" not in session:
        return redirect("/")

    file = request.files.get("file")
    assignment_id = request.form.get("assignment_id")
    student_id = session["user_id"]

    if file and file.filename != "":

        import os
        import time
        import sqlite3

        from AI.evaluator import evaluate_assignment

        # UNIQUE FILE NAME
        filename = f"{assignment_id}_{int(time.time())}_{file.filename}"

        # SAVE STUDENT FILE
        student_pdf = os.path.join(
            app.config["UPLOAD_FOLDER"],
            filename
        )

        file.save(student_pdf)

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row

        # GET ASSIGNMENT
        assignment = conn.execute("""
            SELECT *
            FROM assignments
            WHERE id=?
        """, (assignment_id,)).fetchone()

        question_pdf = os.path.join(
            app.config["UPLOAD_FOLDER"],
            assignment["file_path"]
        )

        # AI EVALUATION
        ai_result = evaluate_assignment(
            question_pdf,
            student_pdf
        )

        print(ai_result)

        # HANDWRITTEN CHECK
        if ai_result["is_handwritten"] == 0:

            conn.close()

            os.remove(student_pdf)

            flash(
                "Only Handwritten Assignments Allowed ❌"
            )

            return redirect(request.referrer)

        # FACULTY FINAL DECISION
        status = "pending"

        conn.execute("""
            INSERT INTO submissions
            (
                assignment_id,
                student_id,
                file_path,
                status,
                ai_status,
                ai_score,
                ai_reason,
                is_handwritten
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            assignment_id,
            student_id,
            filename,
            status,
            ai_result["ai_status"],
            ai_result["ai_score"],
            ai_result["ai_reason"],
            ai_result["is_handwritten"]
        ))

        conn.commit()
        conn.close()

        flash(
            "Assignment Solution Uploaded Successfully ✅"
        )

        return redirect(request.referrer)

    return "<h3>No File Selected ❌</h3>"

# -------- VIEW SUBMISSION --------
@app.route('/view_submissions/<int:assignment_id>')
def view_submissions(assignment_id):
    if session.get('role') != 'faculty':
        return redirect('/login')

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("""
    SELECT submissions.*, students.name 
    FROM submissions
    JOIN students ON submissions.student_id = students.id
    WHERE submissions.assignment_id=?
    """, (assignment_id,))

    submissions = c.fetchall()
    conn.close()

    print("DATA:", submissions)  # 🔥 DEBUG

    return render_template(
        'faculty/view_submissions.html',
        submissions=submissions
    )
@app.route('/view_submission_file/<path:filename>')
def view_submission_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# -------- CREATE ASSIGNMENT--------
@app.route('/create_assignment/<int:unit_id>', methods=['GET', 'POST'])
def create_assignment(unit_id):
    if session.get('role') != 'faculty':
        return redirect('/login')

    if request.method == 'POST':
        title = request.form.get('title')
        file = request.files.get('file')

        filename = None

        if file and file.filename != "":
            filename = f"{unit_id}_{int(time.time())}_{file.filename}"
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        c.execute("""
            INSERT INTO assignments (unit_id, title, file_path)
            VALUES (?, ?, ?)
        """, (unit_id, title, filename))

        conn.commit()
        conn.close()

        return redirect(f'/view_assignments/{unit_id}')

    return render_template('faculty/create_assignment.html', unit_id=unit_id)

# -------- VIEW ASSIGNMENTS --------
@app.route('/view_assignments/<int:unit_id>')
def view_assignments(unit_id):
    if session.get('role') != 'faculty':
        return redirect('/login')

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    assignments = conn.execute(
        "SELECT * FROM assignments WHERE unit_id=?",
        (unit_id,)
    ).fetchall()

    conn.close()

    return render_template(
        'faculty/view_assignments.html',
        assignments=assignments
    )
    # -------- DELETE ASSIGNMENTS --------
@app.route('/delete_assignment/<int:assignment_id>')
def delete_assignment(assignment_id):
    if session.get('role') != 'faculty':
        return redirect('/login')

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT file_path FROM assignments WHERE id=?", (assignment_id,))
    data = c.fetchone()

    if data and data['file_path']:
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], data['file_path'])

        if os.path.exists(file_path):
            os.remove(file_path)

    c.execute("DELETE FROM assignments WHERE id=?", (assignment_id,))
    conn.commit()
    conn.close()

    return redirect(request.referrer)

# ✅ APPROVE
@app.route('/approve/<int:submission_id>')
def approve_submission(submission_id):

    if session.get('role') != 'faculty':
        return redirect('/login')

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    submission = c.execute("""
        SELECT *
        FROM submissions
        WHERE id=?
    """, (submission_id,)).fetchone()

    c.execute("""
        UPDATE submissions
        SET status='approved'
        WHERE id=?
    """, (submission_id,))

    c.execute("""
        INSERT INTO notifications
        (student_id, message)
        VALUES (?, ?)
    """, (
        submission["student_id"],
        "✅ Your assignment has been approved by faculty."
    ))

    conn.commit()
    conn.close()

    return redirect(request.referrer)

# ❌ REJECT
@app.route('/reject/<int:submission_id>')
def reject_submission(submission_id):

    if session.get('role') != 'faculty':
        return redirect('/login')

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    submission = c.execute("""
        SELECT *
        FROM submissions
        WHERE id=?
    """, (submission_id,)).fetchone()

    c.execute("""
        UPDATE submissions
        SET status='rejected'
        WHERE id=?
    """, (submission_id,))

    c.execute("""
        INSERT INTO notifications
        (student_id, message)
        VALUES (?, ?)
    """, (
        submission["student_id"],
        "❌ Your assignment has been rejected by faculty."
    ))

    conn.commit()
    conn.close()

    return redirect(request.referrer)


# -------- NO DUES CERTIFICATE --------
@app.route("/no_dues_certificate")
def no_dues_certificate():

    if "user_id" not in session:
        return redirect("/")

    conn = get_db()

    user = conn.execute(
        "SELECT * FROM students WHERE id=?",
        (session["user_id"],)
    ).fetchone()

    attendance = user["attendance"]

    total_assignments = conn.execute("""

        SELECT COUNT(*)

        FROM assignments a

        JOIN units u ON a.unit_id = u.id
        JOIN subjects s ON u.subject_id = s.id

        WHERE s.dept=?
        AND s.semester=?

    """, (
        user["dept"],
        user["semester"]
    )).fetchone()[0]

    approved = conn.execute("""

        SELECT COUNT(DISTINCT assignment_id)

        FROM submissions

        WHERE student_id=?
        AND status='approved'

    """, (
        session["user_id"],
    )).fetchone()[0]

    pending = total_assignments - approved

    progress = int(
        (approved / total_assignments) * 100
    ) if total_assignments > 0 else 0

    conn.close()

    # STEP 1 : Assignments Check
    if progress < 100:

        return render_template(
            "student/no_dues_locked.html",
            reason=f"{pending} Assignments Remaining"
        )

    # STEP 2 : Attendance Check
    if attendance < 75:

        return render_template(
            "student/no_dues_locked.html",
            reason=f"Attendance Shortage ({attendance}%). Minimum 75% Required"
        )

    # STEP 3 : Generate Certificate
    return render_template(
        "student/no_dues.html",
        user=user
    )
# -------- FACULTY ATTENDANCE --------
@app.route('/faculty/attendance', methods=['GET', 'POST'])
def faculty_attendance():

    if "faculty_id" not in session:
        return redirect('/')

    conn = get_db()

    # Current Faculty
    faculty = conn.execute("""
        SELECT *
        FROM faculty
        WHERE id=?
    """, (session["faculty_id"],)).fetchone()

    # Attendance Permission Check
    if faculty["is_attendance_admin"] != 1:
        conn.close()
        flash("Access Denied")
        return redirect("/faculty_dashboard")

    if request.method == "POST":

        student_id = request.form.get("student_id")
        attendance = request.form.get("attendance")

        conn.execute("""
            UPDATE students
            SET attendance=?
            WHERE id=?
        """, (attendance, student_id))

        conn.commit()

        flash("Attendance Updated Successfully")

    students = conn.execute("""
        SELECT *
        FROM students
        ORDER BY name
    """).fetchall()

    conn.close()

    return render_template(
        "faculty/attendance.html",
        students=students,
        faculty=faculty
    )
    
# -------- STUDENT PROFILE --------
@app.route("/profile")
def student_profile():

    if "user_id" not in session:
        return redirect("/")

    conn = get_db()

    user = conn.execute("""
        SELECT *
        FROM students
        WHERE id=?
    """, (session["user_id"],)).fetchone()

    conn.close()

    return render_template(
        "student/profile.html",
        user=user
    )
    
#-------- FACULTY PROFILE --------
@app.route("/faculty_profile")
def faculty_profile():

    if "faculty_id" not in session:
        return redirect("/")

    conn = get_db()

    faculty = conn.execute("""
        SELECT *
        FROM faculty
        WHERE id=?
    """, (session["faculty_id"],)).fetchone()

    subject_count = conn.execute("""
        SELECT COUNT(*)
        FROM subjects
        WHERE faculty_id=?
    """, (session["faculty_id"],)).fetchone()[0]

    conn.close()

    return render_template(
        "faculty/faculty_profile.html",
        faculty=faculty,
        subject_count=subject_count
    )

# -------- DEPARTMENT DETAILS --------
@app.route('/department-details')
def department_details():

    if "user_id" not in session:
        return redirect("/")

    conn = get_db()

    # Student data
    user = conn.execute(
        "SELECT * FROM students WHERE id=?",
        (session["user_id"],)
    ).fetchone()

    # Subjects + Faculty
    subjects = conn.execute("""
        SELECT
            s.code,
            s.name,
            f.name AS faculty_name
        FROM subjects s
        LEFT JOIN faculty f
        ON s.faculty_id = f.id
    """).fetchall()

    conn.close()

    return render_template(
        "student/department_details.html",
        user=user,
        subjects=subjects
    )
# -------- CHANGE PASSWORD --------
@app.route("/change_password", methods=["GET", "POST"])
def change_password():
    if "user_id" not in session:
        return redirect("/")

    if request.method == "POST":
        old_pass = request.form.get("old_password")
        new_pass = request.form.get("new_password")

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM students WHERE id=?",
            (session["user_id"],)
        ).fetchone()

        if user["password"] != old_pass:
            return "<h3>Old password incorrect ❌</h3>"

        conn.execute(
            "UPDATE students SET password=? WHERE id=?",
            (new_pass, session["user_id"])
        )
        conn.commit()

        return "<h3>Password Updated ✅</h3><a href='/dashboard'>Back</a>"

    return render_template("auth/change_password.html")


# -------- FORGOT PASSWORD --------
@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        enrollment = request.form.get("enrollment")
        new_pass = request.form.get("new_password")

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM students WHERE enrollment=?",
            (enrollment.strip(),)
        ).fetchone()

        if not user:
            return "<h3>Enrollment not found ❌</h3>"

        conn.execute(
            "UPDATE students SET password=? WHERE enrollment=?",
            (new_pass, enrollment.strip())
        )
        conn.commit()

        return "<h3>Password Reset Successful ✅</h3><a href='/'>Login</a>"

    return render_template("auth/forgot_password.html")

@app.route("/mark_notifications_read")
def mark_notifications_read():

    if "user_id" not in session:
        return {"success": False}

    conn = get_db()

    conn.execute("""
        UPDATE notifications
        SET is_read=1
        WHERE student_id=?
        AND is_read=0
    """, (session["user_id"],))

    conn.commit()
    conn.close()

    return {"success": True}


# -------- LOGOUT --------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# -------- RUN --------
if __name__ == "__main__":
    webbrowser.open("http://127.0.0.1:5000")
    app.run(debug=True)

# app.run(
#     host="0.0.0.0",
#     port=5000,
#     debug=True
# )
