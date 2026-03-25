
from flask import Flask, render_template, request, redirect, session, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from openpyxl import Workbook

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "secret")

db_url = os.getenv("DATABASE_URL", "sqlite:///db.sqlite3")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ========= MODELS =========

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    tz = db.Column(db.String(20))

class Seder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    start_time = db.Column(db.String(5))
    amount = db.Column(db.Float)
    deduction = db.Column(db.Float)
    late_minutes = db.Column(db.Integer)

class Day(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    day = db.Column(db.String(10))
    marked = db.Column(db.Boolean)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    tz = db.Column(db.String(20))
    s1 = db.Column(db.String(5))
    s2 = db.Column(db.String(5))
    s3 = db.Column(db.String(5))
    total = db.Column(db.Float)

# ========= LOGIC =========

def calc_total(att):
    sedarim = Seder.query.all()
    times = [att.s1, att.s2, att.s3]
    total = 0

    for i, t in enumerate(times):
        if i >= len(sedarim) or not t:
            continue

        seder = sedarim[i]

        try:
            arrival = datetime.strptime(t, "%H:%M")
            start = datetime.strptime(seder.start_time, "%H:%M")

            diff = (arrival - start).total_seconds() / 60

            if diff <= 0:
                total += seder.amount
            else:
                units = diff // seder.late_minutes
                total += max(0, seder.amount - units * seder.deduction)

        except:
            pass

    return round(total, 2)

# ========= AUTH =========

@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"]).first()
        if user and check_password_hash(user.password, request.form["password"]):
            session["user"] = user.username
            return redirect("/students")
    return render_template("login.html")

# ========= STUDENTS =========

@app.route("/students", methods=["GET","POST"])
def students():
    if request.method == "POST":
        db.session.add(Student(
            name=request.form["name"],
            tz=request.form["tz"]
        ))
        db.session.commit()
    return render_template("students.html", data=Student.query.all())

# ========= SEDARIM =========

@app.route("/sedarim", methods=["GET","POST"])
def sedarim():
    if request.method == "POST":
        db.session.add(Seder(**request.form))
        db.session.commit()
    return render_template("sedarim.html", data=Seder.query.all())

# ========= DAYS =========

@app.route("/days", methods=["GET","POST"])
def days():
    if request.method == "POST":
        db.session.add(Day(
            day=request.form["day"],
            marked=("marked" in request.form)
        ))
        db.session.commit()
    return render_template("days.html", data=Day.query.all())

# ========= ATTENDANCE =========

@app.route("/attendance", methods=["GET","POST"])
def attendance():
    if request.method == "POST":
        att = Attendance(
            name=request.form["name"],
            tz=request.form["tz"],
            s1=request.form["s1"],
            s2=request.form["s2"],
            s3=request.form["s3"]
        )
        att.total = calc_total(att)
        db.session.add(att)
        db.session.commit()

    return render_template("attendance.html", data=Attendance.query.all())

# ========= EXPORT =========

@app.route("/export")
def export():
    wb = Workbook()

    ws = wb.active
    ws.title = "Attendance"

    ws.append(["שם","תז","סדר1","סדר2","סדר3","סכום"])

    for i, r in enumerate(Attendance.query.all(), start=2):
        ws[f"A{i}"] = r.name
        ws[f"B{i}"] = r.tz
        ws[f"C{i}"] = r.s1
        ws[f"D{i}"] = r.s2
        ws[f"E{i}"] = r.s3

        # נוסחה אמיתית
        ws[f"F{i}"] = f"=SUM(C{i}:E{i})"

    filename = f"עדכון נכון ל-{datetime.now().strftime('%Y-%m-%d_%H-%M')}.xlsx"
    wb.save(filename)

    return send_file(filename, as_attachment=True)

# ========= INIT =========

with app.app_context():
    db.create_all()

    if not User.query.first():
        db.session.add(User(
            username="admin",
            password=generate_password_hash("1234")
        ))
        db.session.commit()

# ========= RUN =========

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
