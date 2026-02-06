from flask import Flask, render_template, request, redirect, session, flash, send_from_directory
from werkzeug.utils import secure_filename
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = "secret123"

UPLOAD_FOLDER = "static/proofs"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------- USERS ----------------
users = [
    {"id": 1, "name": "Shreeya", "email": "emp1@company.com", "password": "pass1", "role": "employee"},
    {"id": 2, "name": "Employee Two", "email": "emp2@company.com", "password": "pass2", "role": "employee"},
    {"id": 3, "name": "Employee Three", "email": "emp3@company.com", "password": "pass3", "role": "employee"},
    {"id": 4, "name": "Manager", "email": "manager@company.com", "password": "manager123", "role": "manager"},
    {"id": 5, "name": "HR", "email": "hr@company.com", "password": "hr123", "role": "hr"}
]

leaves = []
next_leave_id = 1

# ---------------- HELPERS ----------------
def get_user(uid):
    for u in users:
        if u["id"] == uid:
            return u
    return None

# ---------------- ROUTES ----------------
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        for u in users:
            if u["email"] == request.form["email"] and u["password"] == request.form["password"]:
                session["user_id"] = u["id"]
                session["name"] = u["name"]
                session["role"] = u["role"]
                return redirect("/dashboard")
        flash("Invalid login!", "danger")
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    uid = session["user_id"]
    role = session["role"]

    if role == "employee":
        my = [l for l in leaves if l["user_id"] == uid]
        sick = sum(l["days"] for l in my if l["type"] == "Sick Leave" and l["status"] == "Approved")
        emergency = sum(l["days"] for l in my if l["type"] == "Emergency Leave" and l["status"] == "Approved")

        limits = {
            "Sick Leave": f"{12 - sick} days left",
            "Emergency Leave": f"{5 - emergency} days left",
            "Casual Leave": "Unlimited",
            "Loss of Pay": "Unlimited"
        }

        return render_template("dashboard.html", role="employee", leaves=my, limits=limits)

    if role == "manager":
        pending = [l for l in leaves if l["status"] == "Pending (Manager)"]
        return render_template("dashboard.html", role="manager", pending=pending, get_user=get_user)

    if role == "hr":
        pending = [l for l in leaves if l["status"] == "Pending (HR)"]
        return render_template("dashboard.html", role="hr", pending=pending, get_user=get_user)

@app.route("/apply", methods=["GET", "POST"])
def apply():
    global next_leave_id
    if request.method == "POST":
        uid = session["user_id"]
        leave_type = request.form["leave_type"]
        start = request.form["from"]
        end = request.form["to"]
        reason = request.form["reason"]

        proof = request.files["proof"]
        filename = secure_filename(str(datetime.now().timestamp()) + "_" + proof.filename)
        proof.save(os.path.join(UPLOAD_FOLDER, filename))

        days = (datetime.strptime(end, "%Y-%m-%d") -
                datetime.strptime(start, "%Y-%m-%d")).days + 1

        # LIMIT CHECK
        approved = [l for l in leaves if l["user_id"] == uid and l["status"] == "Approved"]
        if leave_type == "Sick Leave" and sum(l["days"] for l in approved if l["type"] == leave_type) + days > 12:
            flash("Not eligible – Sick Leave limit exceeded", "danger")
            return redirect("/apply")

        if leave_type == "Emergency Leave" and sum(l["days"] for l in approved if l["type"] == leave_type) + days > 5:
            flash("Not eligible – Emergency Leave limit exceeded", "danger")
            return redirect("/apply")

        leaves.append({
            "id": next_leave_id,
            "user_id": uid,
            "type": leave_type,
            "from": start,
            "to": end,
            "days": days,
            "reason": reason,
            "proof": filename,
            "status": "Pending (Manager)"
        })
        next_leave_id += 1
        flash("Leave applied!", "success")
        return redirect("/dashboard")

    return render_template("apply_leave.html")

@app.route("/m_approve/<int:id>")
def m_approve(id):
    for l in leaves:
        if l["id"] == id:
            l["status"] = "Pending (HR)"
    return redirect("/dashboard")

@app.route("/hr_approve/<int:id>")
def hr_approve(id):
    for l in leaves:
        if l["id"] == id:
            l["status"] = "Approved"
    return redirect("/dashboard")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    app.run(debug=True)
