
from flask import Flask, render_template, request, redirect, session, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, time
import os
from openpyxl import Workbook

app = Flask(__name__)
app.secret_key = "secret"

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", "sqlite:///db.sqlite3")
db = SQLAlchemy(app)

# ================= MODELS =================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))

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

# ================= LOGIC =================

def calc_total(att):
    sedarim = Seder.query.all()
    times = [att.s1, att.s2, att.s3]
    total = 0

    for i, t in enumerate(times):
        if i >= len(sedarim) or not t:
            continue

        seder = sedarim[i]

        try:
            arrival = datetime.strptime(t, "%H:%M").time()
            start = datetime.strptime(seder.start_time, "%H:%M").time()

            diff = (datetime.combine(datetime.today(), arrival) -
                    datetime.combine(datetime.today(), start)).seconds / 60

            if diff <= 0:
                total += seder.amount
            else:
                deduction_units = diff // seder.late_minutes
                total += max(0, seder.amount - deduction_units * seder.deduction)

        except:
            pass

    return round(total, 2)

# ================= ROUTES =================

@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u = User.query.filter_by(
            username=request.form["username"],
            password=request.form["password"]
        ).first()
        if u:
            session["user"] = u.username
            return redirect("/students")
    return render_template("login.html")

@app.route("/students", methods=["GET","POST"])
def students():
    if request.method == "POST":
        db.session.add(Student(name=request.form["name"], tz=request.form["tz"]))
        db.session.commit()
    return render_template("students.html", data=Student.query.all())

@app.route("/sedarim", methods=["GET","POST"])
def sedarim():
    if request.method == "POST":
        db.session.add(Seder(**request.form))
        db.session.commit()
    return render_template("sedarim.html", data=Seder.query.all())

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

@app.route("/export")
def export():
    wb = Workbook()

    ws = wb.active
    ws.title = "Attendance"

    ws.append(["שם","תז","סדר1","סדר2","סדר3","סכום"])

    for r in Attendance.query.all():
        ws.append([r.name, r.tz, r.s1, r.s2, r.s3, r.total])

    name = f"עדכון נכון ל-{datetime.now().strftime('%Y-%m-%d_%H-%M')}.xlsx"
    wb.save(name)

    return send_file(name, as_attachment=True)

# ================= INIT =================

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        if not User.query.first():
            db.session.add(User(username="admin", password="1234"))
            db.session.commit()

    app.run(debug=True)
