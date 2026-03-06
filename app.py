from flask import Flask, render_template, request, redirect, session, url_for, send_from_directory, flash, jsonify
from flask_mail import Mail, Message
import sqlite3
import os
import uuid

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "vgn_secure_fallback_key")

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Email Configuration (Environmental variables recommended for production)
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'your-email@gmail.com')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'your-password')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'your-email@gmail.com')

mail = Mail(app)


@app.template_filter('addslashes')
def addslashes_filter(s):
    if s is None:
        return ""
    return s.replace('\\', '\\\\').replace("'", "\\'").replace('"', '\\"')


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
        previous_work TEXT,
        email TEXT,
        security_experience INTEGER
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

    # Migration: Add email column
    try:
        c.execute("ALTER TABLE applicants ADD COLUMN email TEXT")
    except sqlite3.OperationalError:
        pass

    # Migration: Add security_experience column
    try:
        c.execute("ALTER TABLE applicants ADD COLUMN security_experience INTEGER")
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
    email = request.form["email"]
    security_experience = request.form.get("security_experience")
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

    # Server-side security experience validation
    try:
        sec_exp_val = int(security_experience)
        if sec_exp_val < 1 or sec_exp_val > 10:
            flash("Error: Security experience rating must be between 1 and 10.", "error")
            return redirect(url_for("apply"))
    except (TypeError, ValueError):
        flash("Error: Invalid security experience rating provided.", "error")
        return redirect(url_for("apply"))

    photo = request.files["photo"]

    # Basic extension handling
    photo_ext = os.path.splitext(photo.filename)[1]

    photo_name = applicant_id + "_photo" + photo_ext

    try:
        # Save photo
        photo.save(os.path.join(app.config["UPLOAD_FOLDER"], photo_name))

        conn = sqlite3.connect("database.db")
        c = conn.cursor()

        # Check if NIN already exists
        c.execute("SELECT id FROM applicants WHERE nin = ?", (nin,))
        if c.fetchone():
            conn.close()
            flash("Error: This NIN has already been registered.", "error")
            return redirect(url_for("apply"))

        # Robust INSERT with explicit column names (guarantor set to None)
        c.execute("""
            INSERT INTO applicants (
                id, surname, firstname, phone, address, nin, nok, 
                photo, guarantor, status, age, previous_work, email, security_experience
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (applicant_id, surname, firstname, phone, address, nin, nok,
              photo_name, None, "Pending", age_val, previous_work, email, sec_exp_val))

        conn.commit()
        conn.close()

    except Exception as e:
        print(f"Error during submission: {e}")
        flash("An internal error occurred while processing your application. Please try again later.", "error")
        return redirect(url_for("apply"))

    flash("Application submitted successfully!", "success")
    return render_template("success.html", applicant_id=applicant_id)


# ADMIN LOGIN

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        if username == "admin" and password == "vgn123":
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


@app.route("/approve/<id>", methods=["POST"])
def approve(id):
    if "admin" not in session:
        return redirect(url_for("admin"))

    interview_date = request.form.get("interview_date")
    interview_time = request.form.get("interview_time")
    interview_address = request.form.get("interview_address", "VGN Headquarters, Nigeria")
    applicant_email = request.form.get("applicant_email")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT firstname, surname, phone, email FROM applicants WHERE id=?", (id,))
    applicant = c.fetchone()

    if not applicant:
        conn.close()
        flash("Applicant not found.", "error")
        return redirect(url_for("dashboard"))

    # Use email from form if provided, otherwise fallback to database
    target_email = applicant_email if applicant_email else applicant[3]

    c.execute("UPDATE applicants SET status='Approved' WHERE id=?", (id,))
    conn.commit()
    conn.close()

    # Sending automated email
    try:
        msg = Message("VGN Recruitment - Application Approved",
                      recipients=[target_email])
        msg.body = f"""
        Dear {applicant[0]} {applicant[1]},

        Congratulations! Your application for the Vigilante Group of Nigeria (VGN) has been approved.

        You are hereby invited for an interview scheduled as follows:
        Date: {interview_date}
        Time: {interview_time}
        Address: {interview_address}
        Contact Phone: {admin_phone}

        Please come along with all your original documents.

        Best regards,
        VGN Recruitment Team
        """
        mail.send(msg)
        print(f"Approval email sent to {target_email} for {applicant[0]}")
    except Exception as e:
        print(f"Failed to send email: {e}")

    flash(f"Application for {applicant[0]} {applicant[1]} approved and notification sent.", "success")
    return redirect(url_for("dashboard"))


@app.route("/reject/<id>")
def reject(id):
    if "admin" not in session:
        return redirect(url_for("admin"))

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT firstname, surname, email FROM applicants WHERE id=?", (id,))
    applicant = c.fetchone()

    if not applicant:
        conn.close()
        flash("Applicant not found.", "error")
        return redirect(url_for("dashboard"))

    c.execute("UPDATE applicants SET status='Rejected' WHERE id=?", (id,))
    conn.commit()
    conn.close()

    # Sending automated rejection email
    try:
        msg = Message("VGN Recruitment - Application Status",
                      recipients=[applicant[2]])
        msg.body = f"""
        Dear {applicant[0]} {applicant[1]},

        Thank you for your interest in the Vigilante Group of Nigeria (VGN). 

        After careful review of your application, we regret to inform you that you have not been selected for the next stage at this time (disqualified).

        We wish you the best in your future endeavors.

        Best regards,
        VGN Recruitment Team
        """
        mail.send(msg)
        print(f"Rejection email sent to {applicant[2]} for {applicant[0]}")
    except Exception as e:
        print(f"Failed to send email: {e}")

    flash(f"Application for {applicant[0]} {applicant[1]} has been disqualified and notification sent.", "info")
    return redirect(url_for("dashboard"))


@app.route("/delete/<id>")
def delete_applicant(id):
    if "admin" not in session:
        return redirect(url_for("admin"))

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("DELETE FROM applicants WHERE id=?", (id,))
    conn.commit()
    conn.close()

    flash("Applicant record deleted successfully.", "success")
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
