from flask import Flask, render_template, request, redirect, url_for, session
import firebase_admin
from firebase_admin import credentials, firestore
from google.oauth2 import id_token
from google.auth.transport import requests
from datetime import datetime, timezone
import bleach
import uuid

# ================= FIREBASE =================
cred = credentials.Certificate("serviceAccountKey.json")

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ================= APP =================
app = Flask(__name__)
app.secret_key = "your_super_secret_key"

CLIENT_ID = "737562037990-n21m7uc217rhihqs83r5j5hene4b2jf6.apps.googleusercontent.com"

# ================= LOGIN =================
def login_required(f):
    def wrapper(*args, **kwargs):
        if 'uid' not in session:
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper


@app.route("/")
def index():
    return render_template("admin_log_in.html")


# ================= GOOGLE AUTH =================
@app.route("/google-auth", methods=["POST"])
def login_g_auth():
    token = request.form["token"]

    try:
        google_account = id_token.verify_oauth2_token(
            token, requests.Request(), CLIENT_ID
        )

        session["uid"] = google_account["sub"]
        session["email"] = google_account["email"]
        session["name"] = google_account.get("name", "User")

        db.collection("users").document(session["uid"]).set({
            "email": session["email"],
            "name": session["name"],
            "last_login": datetime.now(timezone.utc)
        }, merge=True)

        return redirect(url_for("admin_dashboard"))

    except Exception:
        return "Invalid Login", 400


# ================= ADMIN DASHBOARD =================
@app.route("/admin_dashboard", methods=["GET", "POST"])
@login_required
def admin_dashboard():

    if request.method == "POST":
        uid = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        tons = safe_float(request.form.get("tons"))
        price = safe_float(request.form.get("price"))

        db.collection("assignments").document(uid).set({
            "Customer_Name": bleach.clean(request.form.get("CustomerName", "")),
            "location": bleach.clean(request.form.get("location", "")),

            "tons": tons,
            "price": price,
            "income": tons * price,
            "profit": 0,

            "status": "pending",
            "is_accepted": False,

            "timestamp": now,
            "date_assigned": now.strftime("%Y-%m-%d %H:%M:%S"),

            "fuel_cost": 0,
            "distance": 0
        })

        return redirect(url_for("admin_dashboard"))

    docs = db.collection("assignments").stream()

    data = []
    for doc in docs:
        item = doc.to_dict()
        item["id"] = doc.id
        data.append(item)

    history = [x for x in data if x.get("status") == "done"]

    total_income = sum(float(x.get("income", 0)) for x in history)
    total_fuel = sum(float(x.get("fuel_cost", 0)) for x in history)

    profit = total_income - total_fuel

    daily = profit
    weekly = profit
    monthly = profit
    return render_template(
    "admin_dashboard.html",
    Input_Dashboard=data,
    history=history,
    daily=daily,
    weekly=weekly,
    monthly=monthly,
    total_income=total_income,
    total_fuel=total_fuel
)

# ================= ADMIN STATUS =================
@app.route("/admin_status")
@login_required
def admin_status():
    docs = db.collection("assignments").stream()

    data = []
    for doc in docs:
        item = doc.to_dict()
        item["id"] = doc.id
        data.append(item)

    return render_template("admin_status.html", Input_Dashboard=data)


# ================= DRIVER PAGE =================
@app.route("/driver")
@login_required
def driver():
    docs = db.collection("assignments").stream()

    data = []
    for doc in docs:
        item = doc.to_dict()
        item["id"] = doc.id
        data.append(item)

    return render_template("driver_side.html", Input_Dashboard=data)


# ================= ACCEPT =================
@app.route("/accept_delivery/<id>", methods=["POST"])
@login_required
def accept_delivery(id):
    db.collection("assignments").document(id).update({
        "status": "accepted",
        "is_accepted": True
    })
    return redirect(url_for("driver"))


# ================= DECLINE =================
@app.route("/decline_delivery/<id>", methods=["POST"])
@login_required
def decline_delivery(id):
    db.collection("assignments").document(id).update({
        "status": "declined",
        "is_accepted": False
    })
    return redirect(url_for("driver"))


# ================= DRIVER COMPLETE =================
@app.route("/driver_update/<id>", methods=["POST"])
@login_required
def driver_update(id):

    start = safe_float(request.form.get("startOdo"))
    end = safe_float(request.form.get("endOdo"))
    fuel = safe_float(request.form.get("FuelUsed"))
    price = safe_float(request.form.get("FuelPrice"))

    distance = max(0, end - start)
    fuel_cost = fuel * price

    doc = db.collection("assignments").document(id).get().to_dict()

    income = float(doc.get("income", 0))
    profit = income - fuel_cost

    db.collection("assignments").document(id).update({
        "distance": distance,
        "fuel_cost": fuel_cost,
        "profit": profit,
        "status": "done",
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d")
    })

    return redirect(url_for("driver"))


# ================= DELETE (OPTIONAL) =================
@app.route("/delete/<id>", methods=["POST"])
@login_required
def delete(id):
    db.collection("assignments").document(id).delete()
    return redirect(url_for("admin_dashboard"))


# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# ================= SAFE FLOAT =================
def safe_float(value):
    try:
        return float(value)
    except:
        return 0.0


# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)