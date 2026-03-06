from flask import Flask, render_template, request, redirect, session, url_for, send_from_directory, flash
import sqlite3
import os
import uuid

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "vgn_secure_fallback_key")

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS applicants(
        id TEXT PRIMARY KEY,
        surname TEXT,
        firstname TEXT,
        phone TEXT,
        address TEXT,
        nin TEXT UNIQUE,
        nok TEXT,
        photo TEXT,
        guarantor TEXT,
        status TEXT,
        age INTEGER,
        previous_work TEXT
    )
    """)

    # Migration: Add age column if it doesn't exist (for existing databases)
    try:
        c.execute("ALTER TABLE applicants ADD COLUMN age INTEGER")
    except sqlite3.OperationalError:
        pass

    # Migration: Add previous_work column if it doesn't exist
    try:
        c.execute("ALTER TABLE applicants ADD COLUMN previous_work TEXT")
    except sqlite3.OperationalError:
        pass

    # Ensure NIN is unique if it wasn't already (for existing tables)
    try:
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_applicants_nin ON applicants(nin)")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()


init_db()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/apply")
def apply():
    return render_template("apply.html")


@app.route("/submit", methods=["POST"])
def submit():
    applicant_id = str(uuid.uuid4())[:8]

    surname = request.form["surname"]
    firstname = request.form["firstname"]
    phone = request.form["phone"]
    age = request.form.get("age")
    address = request.form["address"]
    nin = request.form["nin"]
    nok = request.form["nok"]
    previous_work_list = request.form.getlist("previous_work")
    # Filter out empty strings and join with a semicolon
    previous_work = "; ".join([w.strip() for w in previous_work_list if w.strip()])

    # Server-side age validation
    try:
        age_val = int(age)
        if age_val < 20:
            flash("Error: You must be at least 20 years old to apply.", "error")
            return redirect(url_for("apply"))
    except (TypeError, ValueError):
        flash("Error: Invalid age provided.", "error")
        return redirect(url_for("apply"))

    photo = request.files["photo"]
    guarantor = request.files["guarantor"]

    # Basic extension handling
    photo_ext = os.path.splitext(photo.filename)[1]
    guarantor_ext = os.path.splitext(guarantor.filename)[1]

    photo_name = applicant_id + "_photo" + photo_ext
    guarantor_name = applicant_id + "_guarantor" + guarantor_ext

    photo.save(os.path.join(app.config["UPLOAD_FOLDER"], photo_name))
    guarantor.save(os.path.join(app.config["UPLOAD_FOLDER"], guarantor_name))

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    # Check if NIN already exists
    c.execute("SELECT id FROM applicants WHERE nin = ?", (nin,))
    if c.fetchone():
        conn.close()
        flash("Error: This NIN has already been registered.", "error")
        return redirect(url_for("apply"))

    c.execute("INSERT INTO applicants VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
              (applicant_id, surname, firstname, phone, address, nin, nok, photo_name, guarantor_name, "Pending",
               age_val, previous_work))

    conn.commit()
    conn.close()

    flash("Application submitted successfully!", "success")
    return render_template("success.html", applicant_id=applicant_id)


# ADMIN LOGIN

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        if username == "admin" and password == "1@WrongPwd":
            session["admin"] = True
            return redirect(url_for("dashboard"))

    return render_template("admin_login.html")


@app.route("/dashboard")
def dashboard():
    if "admin" not in session:
        return redirect(url_for("admin"))

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    # Get all applicants, newest first
    c.execute("SELECT * FROM applicants ORDER BY rowid DESC")
    applicants = c.fetchall()

    conn.close()

    return render_template("dashboard.html", applicants=applicants)


@app.route("/approve/<id>")
def approve(id):
    if "admin" not in session:
        return redirect(url_for("admin"))

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("UPDATE applicants SET status='Approved' WHERE id=?", (id,))

    conn.commit()
    conn.close()

    return redirect(url_for("dashboard"))


@app.route("/reject/<id>")
def reject(id):
    if "admin" not in session:
        return redirect(url_for("admin"))

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("UPDATE applicants SET status='Rejected' WHERE id=?", (id,))

    conn.commit()
    conn.close()

    return redirect(url_for("dashboard"))


@app.route("/check_status", methods=["GET", "POST"])
def check_status():
    status_data = None
    error = None

    if request.method == "POST":
        applicant_id = request.form.get("applicant_id", "").strip()

        if not applicant_id:
            error = "Please enter an Applicant ID."
        else:
            conn = sqlite3.connect("database.db")
            c = conn.cursor()
            c.execute("SELECT * FROM applicants WHERE id=?", (applicant_id,))
            status_data = c.fetchone()
            conn.close()

            if not status_data:
                error = "No application found with that ID. Please check and try again."

    return render_template("check_status.html", status_data=status_data, error=error)


@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("home"))


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    if "admin" not in session:
        return "Unauthorized", 401
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


if __name__ == "__main__":
    app.run(debug=True)
