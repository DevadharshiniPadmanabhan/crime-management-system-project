from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3

app = Flask(__name__)
app.secret_key = "secretkey"

# ---------- DATABASE CONNECTION ----------
def get_db():
    conn = sqlite3.connect("database1.db")
    conn.row_factory = sqlite3.Row
    return conn

# ---------- CREATE TABLES ----------
def create_tables():
    conn = get_db()
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        aadhaar TEXT UNIQUE,
        dob TEXT
    )
    """)

    # FIR table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fir (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        complainant_name TEXT,
        crime_type TEXT,
        crime_date TEXT,
        location TEXT,
        description TEXT,
        status TEXT DEFAULT 'Incompleted'
    )
    """)

    # Evidence table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS evidence (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fir_id INTEGER,
        officer_name TEXT,
        evidence_type TEXT,
        evidence_desc TEXT,
        FOREIGN KEY(fir_id) REFERENCES fir(id)
    )
    """)

    conn.commit()
    conn.close()

# ---------- LOGIN ----------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        aadhaar = request.form["aadhaar"]
        dob = request.form["dob"]

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE aadhaar=? AND dob=?",
            (aadhaar, dob)
        )
        user = cursor.fetchone()
        conn.close()

        if user:
            session["user"] = aadhaar
            return redirect(url_for("dashboard"))
        else:
            return "Invalid Aadhaar or DOB"

    return render_template("login.html")

# ---------- REGISTER USER ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        aadhaar = request.form["aadhaar"]
        dob = request.form["dob"]

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (aadhaar, dob) VALUES (?, ?)",
            (aadhaar, dob)
        )
        conn.commit()
        conn.close()

        return redirect(url_for("login"))

    return render_template("register.html")

# ---------- DASHBOARD ----------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    # Total cases
    cursor.execute("SELECT COUNT(*) FROM fir")
    total_cases = cursor.fetchone()[0]

    # Completed & Incompleted
    cursor.execute("SELECT COUNT(*) FROM fir WHERE status='Completed'")
    completed = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM fir WHERE status='Incompleted'")
    incompleted = cursor.fetchone()[0]

    # Current month crime-type data
    cursor.execute("""
        SELECT crime_type, COUNT(*) 
        FROM fir
        WHERE strftime('%Y-%m', crime_date) = strftime('%Y-%m', 'now')
        GROUP BY crime_type
    """)
    rows = cursor.fetchall()
    conn.close()

    total_month = sum(count for _, count in rows) or 1

    chart_data = []
    for crime_type, count in rows:
        percent = int((count / total_month) * 100)
        chart_data.append({
            "crime_type": crime_type,
            "count": count,
            "percent": percent
        })

    return render_template(
        "dashboard.html",
        total_cases=total_cases,
        completed=completed,
        incompleted=incompleted,
        chart_data=chart_data
    )

# ---------- REGISTER FIR ----------
@app.route("/register_fir", methods=["GET", "POST"])
def register_fir():
    if "user" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        complainant_name = request.form["complainant_name"]
        crime_type = request.form["crime_type"]
        crime_date = request.form["crime_date"]
        location = request.form["location"]
        description = request.form["description"]
        status = request.form.get("status", "Incompleted")

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO fir 
            (complainant_name, crime_type, crime_date, location, description, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (complainant_name, crime_type, crime_date, location, description, status)
        )
        conn.commit()
        conn.close()

        return redirect(url_for("fir_submitted"))

    return render_template("add_fir.html")

# ---------- FIR SUBMITTED ----------
@app.route("/fir_submitted")
def fir_submitted():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("fir_submitted.html")

# ---------- VIEW CASES ----------
@app.route("/view_cases")
def view_cases():
    if "user" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM fir")
    cases = cursor.fetchall()
    conn.close()

    return render_template("cases.html", cases=cases)

# ---------- UPDATE STATUS ----------
@app.route("/update_status/<int:case_id>", methods=["POST"])
def update_status(case_id):
    if "user" not in session:
        return redirect(url_for("login"))

    new_status = request.form["status"]

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE fir SET status=? WHERE id=?",
        (new_status, case_id)
    )
    conn.commit()
    conn.close()

    return redirect(url_for("view_cases"))

# ---------- ADD EVIDENCE ----------
@app.route("/add_evidence/<int:case_id>", methods=["GET", "POST"])
def add_evidence(case_id):
    if "user" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        officer_name = request.form["officer_name"]
        etype = request.form["evidence_type"]
        edesc = request.form["description"]

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO evidence(fir_id, officer_name, evidence_type, evidence_desc)
            VALUES (?, ?, ?, ?)
        """, (case_id, officer_name, etype, edesc))
        conn.commit()
        conn.close()

        return redirect(url_for("case_history", case_id=case_id))

    return render_template("add_evidence.html", case_id=case_id)

# ---------- CASE HISTORY ----------
@app.route("/case_history/<int:case_id>")
def case_history(case_id):
    if "user" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM fir WHERE id=?", (case_id,))
    case = cursor.fetchone()

    cursor.execute("SELECT * FROM evidence WHERE fir_id=?", (case_id,))
    evidence = cursor.fetchall()
    conn.close()

    return render_template(
        "case_history.html",
        case=case,
        evidence=evidence
    )

# ---------- ANALYTICS ----------
@app.route("/analytics")
def analytics():
    if "user" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM fir")
    total_firs = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM fir WHERE status='Incompleted'")
    active_cases = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM fir WHERE status='Completed'")
    closed_cases = cursor.fetchone()[0]

    cursor.execute("""
        SELECT crime_type, COUNT(*) 
        FROM fir 
        GROUP BY crime_type
    """)
    crime_data = cursor.fetchall()

    conn.close()

    return render_template(
        "analytics.html",
        total_firs=total_firs,
        active_cases=active_cases,
        closed_cases=closed_cases,
        crime_data=crime_data
    )

# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ---------- RUN ----------
if __name__ == "__main__":
    create_tables()
    app.run(debug=True)
