
import os
from flask import Flask, render_template, request, redirect, session, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from openpyxl import Workbook

app = Flask(__name__)
app.secret_key = "secret"

db_url = os.getenv("DATABASE_URL", "sqlite:///db.sqlite3")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://","postgresql://",1)

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# ---------------- MODELS ----------------

class User(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    username=db.Column(db.String(100),unique=True)
    password=db.Column(db.String(200))

class Student(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String(100))
    tz=db.Column(db.String(20))

class Seder(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String(100))
    start_time=db.Column(db.String(5))
    amount=db.Column(db.Float)
    deduction=db.Column(db.Float)
    late_minutes=db.Column(db.Integer)

class Day(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    day=db.Column(db.String(10))
    marked=db.Column(db.Boolean)

class Attendance(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    student_id=db.Column(db.Integer,db.ForeignKey("student.id"))
    s1=db.Column(db.String(5))
    s2=db.Column(db.String(5))
    s3=db.Column(db.String(5))
    total=db.Column(db.Float)
    student=db.relationship("Student")

# ---------------- LOGIN ----------------

@app.route("/",methods=["GET","POST"])
def login():
    if request.method=="POST":
        user=User.query.filter_by(username=request.form["username"]).first()
        if user and check_password_hash(user.password,request.form["password"]):
            session["user"]=user.username
            return redirect("/students")
    return render_template("login.html")

def login_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*a,**kw):
        if "user" not in session:
            return redirect("/")
        return f(*a,**kw)
    return wrapper

# ---------------- STUDENTS ----------------

@app.route("/students",methods=["GET","POST"])
@login_required
def students():
    if request.method=="POST":
        s=Student(name=request.form["name"],tz=request.form["tz"])
        db.session.add(s)
        db.session.commit()
    return render_template("students.html",data=Student.query.all())

# ---------------- SEDARIM ----------------

@app.route("/sedarim",methods=["GET","POST"])
@login_required
def sedarim():
    if request.method=="POST":
        s=Seder(
            name=request.form["name"],
            start_time=request.form["start_time"],
            amount=float(request.form["amount"]),
            deduction=float(request.form["deduction"]),
            late_minutes=int(request.form["late_minutes"])
        )
        db.session.add(s)
        db.session.commit()
    return render_template("sedarim.html",data=Seder.query.all())

# ---------------- DAYS ----------------

@app.route("/days",methods=["GET","POST"])
@login_required
def days():
    if request.method=="POST":
        d=Day(day=request.form["day"],marked=("marked" in request.form))
        db.session.add(d)
        db.session.commit()
    return render_template("days.html",data=Day.query.all())

# ---------------- CALC ----------------

def calc_total(att):
    sedarim=Seder.query.order_by(Seder.id).all()
    times=[att.s1,att.s2,att.s3]
    total=0
    for i,t in enumerate(times):
        if i>=len(sedarim) or not t:
            continue
        seder=sedarim[i]
        try:
            arrival=datetime.strptime(t,"%H:%M")
            start=datetime.strptime(seder.start_time,"%H:%M")
            diff=(arrival-start).total_seconds()/60
            if diff<=0:
                total+=seder.amount
            else:
                units=diff//seder.late_minutes
                total+=max(0,seder.amount-units*seder.deduction)
        except:
            pass
    return round(total,2)

# ---------------- ATTENDANCE ----------------

@app.route("/attendance",methods=["GET","POST"])
@login_required
def attendance():
    students=Student.query.all()
    sedarim=Seder.query.order_by(Seder.id).all()

    if request.method=="POST":
        att=Attendance(
            student_id=request.form["student_id"],
            s1=request.form["s1"],
            s2=request.form["s2"],
            s3=request.form["s3"]
        )
        att.total=calc_total(att)
        db.session.add(att)
        db.session.commit()

    return render_template("attendance.html",
        data=Attendance.query.all(),
        students=students,
        sedarim=sedarim
    )

# ---------------- EXPORT ----------------

@app.route("/export")
@login_required
def export():

    wb=Workbook()

    ws=wb.active
    ws.title="Students"
    ws.append(["שם","תז"])
    for s in Student.query.all():
        ws.append([s.name,s.tz])

    ws2=wb.create_sheet("Sedarim")
    ws2.append(["שם סדר","התחלה","סכום"])
    for s in Seder.query.all():
        ws2.append([s.name,s.start_time,s.amount])

    ws3=wb.create_sheet("Days")
    ws3.append(["יום","סימון"])
    for d in Day.query.all():
        ws3.append([d.day,d.marked])

    ws4=wb.create_sheet("Attendance")
    ws4.append(["שם","תז","ס1","ס2","ס3","סכום"])
    for i,a in enumerate(Attendance.query.all(),start=2):
        ws4[f"A{i}"]=a.student.name
        ws4[f"B{i}"]=a.student.tz
        ws4[f"C{i}"]=a.s1
        ws4[f"D{i}"]=a.s2
        ws4[f"E{i}"]=a.s3
        ws4[f"F{i}"]=a.total

    filename=f"עדכון נכון ל-{datetime.now().strftime('%Y-%m-%d_%H-%M')}.xlsx"
    wb.save(filename)
    return send_file(filename,as_attachment=True)

# ---------------- INIT ----------------

with app.app_context():
    db.create_all()
    if not User.query.first():
        db.session.add(User(username="admin",password=generate_password_hash("1234")))
        db.session.commit()

if __name__=="__main__":
    app.run(host="0.0.0.0",port=10000)
