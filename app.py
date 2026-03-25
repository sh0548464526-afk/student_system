
from flask import Flask,render_template,request,redirect,jsonify,send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager,UserMixin,login_user,login_required,logout_user
import datetime,openpyxl,os

app=Flask(__name__)
app.secret_key="secret"

app.config["SQLALCHEMY_DATABASE_URI"]=os.getenv("DATABASE_URL","sqlite:///db.sqlite3")
db=SQLAlchemy(app)

login_manager=LoginManager(app)
login_manager.login_view="login"

class User(UserMixin,db.Model):
 id=db.Column(db.Integer,primary_key=True)
 username=db.Column(db.String)
 password=db.Column(db.String)
 role=db.Column(db.String)

class Student(db.Model):
 id=db.Column(db.Integer,primary_key=True)
 name=db.Column(db.String)
 tz=db.Column(db.String)

class Seder(db.Model):
 id=db.Column(db.Integer,primary_key=True)
 name=db.Column(db.String)
 start=db.Column(db.String)
 amount=db.Column(db.Integer)
 late=db.Column(db.Integer)
 deduct=db.Column(db.Integer)

class Day(db.Model):
 id=db.Column(db.Integer,primary_key=True)
 day=db.Column(db.Integer)
 active=db.Column(db.Boolean)

class Attendance(db.Model):
 id=db.Column(db.Integer,primary_key=True)
 student_id=db.Column(db.Integer,db.ForeignKey("student.id"))
 day=db.Column(db.Integer)
 s1=db.Column(db.String)
 s2=db.Column(db.String)
 s3=db.Column(db.String)
 total=db.Column(db.Integer)

 student=db.relationship("Student")

@login_manager.user_loader
def load_user(id):
 return User.query.get(int(id))

def minutes(t):
 h,m=map(int,t.split(":"))
 return h*60+m

def calc(arrive,start,late,amount,deduct):
 if not arrive:return 0
 diff=minutes(arrive)-minutes(start)
 if diff<=late:return amount
 return max(amount-deduct,0)

@app.route("/",methods=["GET","POST"])
def login():
 if request.method=="POST":
  u=User.query.filter_by(username=request.form["u"]).first()
  if u and u.password==request.form["p"]:
   login_user(u)
   return redirect("/attendance")
 return render_template("login.html")

@app.route("/logout")
def logout():
 logout_user()
 return redirect("/")

@app.route("/students",methods=["GET","POST"])
@login_required
def students():
 if request.method=="POST":
  db.session.add(Student(name=request.form["name"],tz=request.form["tz"]))
  db.session.commit()
 return render_template("students.html",data=Student.query.all())

@app.route("/sedarim",methods=["GET","POST"])
@login_required
def sedarim():
 if request.method=="POST":
  db.session.add(Seder(
   name=request.form["name"],
   start=request.form["start"],
   amount=request.form["amount"],
   late=request.form["late"],
   deduct=request.form["deduct"]))
  db.session.commit()
 return render_template("sedarim.html",data=Seder.query.all())

@app.route("/days",methods=["GET","POST"])
@login_required
def days():
 if request.method=="POST":
  for i in range(1,31):
   val=("d"+str(i)) in request.form
   d=Day.query.filter_by(day=i).first()
   if not d: d=Day(day=i)
   d.active=val
   db.session.add(d)
  db.session.commit()
 return render_template("days.html",data=Day.query.all())

@app.route("/attendance")
@login_required
def attendance():
 students=Student.query.all()
 sedarim=Seder.query.order_by(Seder.id).all()
 days=[d.day for d in Day.query.filter_by(active=True).all()]
 data=Attendance.query.all()
 return render_template("attendance.html",students=students,sedarim=sedarim,days=days,data=data)

@app.route("/save",methods=["POST"])
@login_required
def save():
 s=request.json
 sedarim=Seder.query.order_by(Seder.id).all()

 total=0
 arr=[s["s1"],s["s2"],s["s3"]]

 for i in range(len(sedarim)):
  total+=calc(arr[i],sedarim[i].start,sedarim[i].late,sedarim[i].amount,sedarim[i].deduct)

 a=Attendance(student_id=s["student"],day=s["day"],s1=s["s1"],s2=s["s2"],s3=s["s3"],total=total)
 db.session.add(a)
 db.session.commit()

 return jsonify({"ok":True})

@app.route("/excel")
@login_required
def excel():
 wb=openpyxl.Workbook()
 ws=wb.active
 ws.append(["תלמיד","יום","סדר1","סדר2","סדר3","סכום"])
 for a in Attendance.query.all():
  ws.append([a.student.name,a.day,a.s1,a.s2,a.s3,a.total])
 name="attendance.xlsx"
 wb.save(name)
 return send_file(name,as_attachment=True)

@app.route("/reset")
@login_required
def reset():
 db.drop_all()
 db.create_all()
 return "db reset"

with app.app_context():
 db.create_all()
 if not User.query.first():
  db.session.add(User(username="admin",password="1234",role="admin"))
  db.session.commit()

if __name__=="__main__":
 app.run()
