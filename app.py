
from flask import Flask,render_template,request,redirect,send_file
from flask_sqlalchemy import SQLAlchemy
import os,datetime,openpyxl

app=Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"]=os.getenv("DATABASE_URL","sqlite:///db.sqlite3")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"]=False
db=SQLAlchemy(app)

class Student(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String)

class Day(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String)
    active=db.Column(db.Boolean,default=True)

class Seder(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String)
    amount=db.Column(db.Integer)
    late_minutes=db.Column(db.Integer)
    deduction=db.Column(db.Integer)

class Attendance(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    student_id=db.Column(db.Integer,db.ForeignKey("student.id"))
    day_id=db.Column(db.Integer,db.ForeignKey("day.id"))
    s1=db.Column(db.String)
    s2=db.Column(db.String)
    s3=db.Column(db.String)
    total=db.Column(db.Integer)

    student=db.relationship("Student")
    day=db.relationship("Day")

def calc_total():
    sedarim=Seder.query.order_by(Seder.id).all()
    return sum([s.amount for s in sedarim])

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/students",methods=["GET","POST"])
def students():
    if request.method=="POST":
        db.session.add(Student(name=request.form["name"]))
        db.session.commit()
        return redirect("/students")
    return render_template("students.html",data=Student.query.all())

@app.route("/days",methods=["GET","POST"])
def days():
    if request.method=="POST":
        db.session.add(Day(name=request.form["name"],active="active" in request.form))
        db.session.commit()
        return redirect("/days")
    return render_template("days.html",data=Day.query.all())

@app.route("/sedarim",methods=["GET","POST"])
def sedarim():
    if request.method=="POST":
        db.session.add(Seder(
        name=request.form["name"],
        amount=request.form["amount"],
        late_minutes=request.form["late"],
        deduction=request.form["deduct"]))
        db.session.commit()
        return redirect("/sedarim")
    return render_template("sedarim.html",data=Seder.query.all())

@app.route("/attendance",methods=["GET","POST"])
def attendance():
    students=Student.query.all()
    days=Day.query.filter_by(active=True).all()
    sedarim=Seder.query.order_by(Seder.id).all()

    if request.method=="POST":
        a=Attendance(
        student_id=request.form["student"],
        day_id=request.form["day"],
        s1=request.form["s1"],
        s2=request.form["s2"],
        s3=request.form["s3"],
        total=calc_total()
        )
        db.session.add(a)
        db.session.commit()
        return redirect("/attendance")

    data=Attendance.query.all()
    return render_template("attendance.html",data=data,students=students,days=days,sedarim=sedarim)

@app.route("/settings")
def settings():
    return render_template("settings.html")

@app.route("/resetdb")
def resetdb():
    db.drop_all()
    db.create_all()
    return "database recreated"

@app.route("/excel")
def excel():
    wb=openpyxl.Workbook()
    ws=wb.active
    ws.append(["תלמיד","יום","סכום"])
    for a in Attendance.query.all():
        ws.append([a.student.name,a.day.name,a.total])
    name="report.xlsx"
    wb.save(name)
    return send_file(name,as_attachment=True)

with app.app_context():
    db.create_all()

if __name__=="__main__":
    app.run()
