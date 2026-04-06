from flask import Flask, abort, render_template, request, redirect, url_for, flash, session
import firebase_admin
from firebase_admin import credentials, firestore
from google.oauth2 import id_token
from google.auth.transport import requests
from datetime import datetime, UTC
import bleach
import uuid
from werkzeug.security import generate_password_hash, check_password_hash

# ================= FIREBASE =================
cred = credentials.Certificate("serviceAccountKey.json")
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()
app = Flask(__name__)


# ================= LOGIN =================
@app.route("/")
def index():
    return render_template("admin_log_in.html")


@app.route("/google-auth", methods=["POST"])
def login_g_auth():
    token = request.form["token"]
    
    try:
        google_account = id_token.verify_oauth2_token(token, requests.Request(), CLIENT_ID)
        
        # Store user info in session
        session['uid'] = google_account["sub"]
        session['email'] = google_account["email"]
        session['name'] = google_account.get("name", "User")

        db.collection(google_create_account).document(session['uid']).set({
            "uid": session['uid'],
            "email": session['email'],
            "name": session['name'],
            "provider": "google",
            "last_login": datetime.now(UTC).isoformat()
        }, merge=True)

        return redirect(url_for("admin_dashboard")) 
    except ValueError:
        return render_template("error.html", message="Invalid Google token")


# ================= ADMIN DASHBOARD =================
@app.route("/admin_dashboard", methods=["GET", "POST"])
def admin_dashboard():

    if request.method == "POST":
        uid = str(uuid.uuid4())
        now = datetime.now()

        tons = float(request.form.get("tons", 0))
        price = float(request.form.get("price", 0))
        income = tons * price

        db.collection("assignments").document(uid).set({
            "Customer_Name": request.form.get("CustomerName", ""),
            "Admin_Vehicle": request.form.get("Vehicle", ""),
            "Admin_DriverS": request.form.get("Driver", ""),

            "tons": tons,
            "price_per_ton": price,
            "income": income,
            "profit": 0,

            "status": "pending",
            "is_accepted": False,

            "timestamp": now,

            "assigned_date": now.strftime("%Y-%m-%d"),
            "assigned_time": now.strftime("%H:%M:%S"),

            "accepted_date": "",
            "accepted_time": "",

            "fuel_cost": 0,
            "distance": 0,

            "date": "",
            "time": ""
        })

        return redirect(url_for("admin_dashboard"))

    docs = db.collection("assignments").order_by("timestamp", direction=firestore.Query.DESCENDING).stream()

    data = []
    for doc in docs:
        item = doc.to_dict()
        item["id"] = doc.id

        # SAFE DEFAULTS
        item.setdefault("profit", 0)
        item.setdefault("fuel_cost", 0)
        item.setdefault("distance", 0)

        data.append(item)

    # SORT STATUS
    status_priority = {"pending": 0, "transit": 1, "done": 2}
    data.sort(key=lambda x: status_priority.get(x.get("status"), 3))

    # HISTORY
    history = [x for x in data if x.get("status") == "done"]
    history.sort(key=lambda x: x.get("timestamp"), reverse=True)

    # INCOME CALCULATION
    today = datetime.now()
    daily = weekly = monthly = 0

    for item in history:
        income = float(item.get("income", 0))
        date_str = item.get("date")

        if not date_str:
            continue

        d = datetime.strptime(date_str, "%Y-%m-%d")

        if d.date() == today.date():
            daily += income

        if (today - d).days <= 7:
            weekly += income

        if d.month == today.month and d.year == today.year:
            monthly += income

    return render_template(
        "admin_dashboard.html",
        Input_Dashboard=data,
        history=history,
        daily=daily,
        weekly=weekly,
        monthly=monthly
    )


# ================= ADMIN STATUS =================
@app.route("/admin_status")
def admin_status():
    docs = db.collection("assignments").order_by("timestamp", direction=firestore.Query.DESCENDING).stream()

    data = []
    for doc in docs:
        item = doc.to_dict()
        item["id"] = doc.id

        item.setdefault("profit", 0)
        item.setdefault("fuel_cost", 0)

        data.append(item)

    return render_template("admin_status.html", Input_Dashboard=data)


# ================= DELETE =================
@app.route("/delete/<id>")
def delete(id):
    db.collection("assignments").document(id).delete()
    return redirect(url_for("admin_dashboard"))


# ================= DRIVER =================
@app.route("/driver")
def driver():
    docs = db.collection("assignments").order_by("timestamp", direction=firestore.Query.DESCENDING).stream()

    data = []
    for doc in docs:
        item = doc.to_dict()
        item["id"] = doc.id
        item.setdefault("is_accepted", False)
        data.append(item)

    return render_template("driver_side.html", Input_Dashboard=data)


# ================= ACCEPT =================
@app.route("/accept_delivery/<id>", methods=["POST"])
def accept_delivery(id):
    now = datetime.now()

    db.collection("assignments").document(id).update({
        "status": "transit",
        "is_accepted": True,
        "accepted_date": now.strftime("%Y-%m-%d"),
        "accepted_time": now.strftime("%H:%M:%S")
    })

    return redirect(url_for("driver"))


# ================= DRIVER UPDATE =================
@app.route("/driver_update/<id>", methods=["POST"])
def driver_update(id):

    start = float(request.form.get("startOdo", 0))
    end = float(request.form.get("endOdo", 0))
    fuel = float(request.form.get("fuel", 0))
    price = float(request.form.get("price", 0))

    distance = max(0, end - start)
    fuel_cost = fuel * price

    doc = db.collection("assignments").document(id).get().to_dict()
    income = float(doc.get("income", 0))
    profit = income - fuel_cost

    now = datetime.now()

    db.collection("assignments").document(id).update({
        "fuel_cost": fuel_cost,
        "distance": distance,
        "profit": profit,
        "status": "done",
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S")
    })

    return redirect(url_for("driver"))


if __name__ == "__main__":
    app.run(debug=True)