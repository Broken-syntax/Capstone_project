    from flask import Flask, abort, render_template, request, redirect, url_for, flash, session
    import firebase_admin
    from firebase_admin import credentials, firestore
    from google.oauth2 import id_token
    from google.auth.transport import requests
    from datetime import datetime, UTC
    import bleach
    import uuid
    from werkzeug.security import generate_password_hash, check_password_hash

    cred = credentials.Certificate("serviceAccountKey.json")
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)

    db = firestore.client()

    CLIENT_ID = "737562037990-n21m7uc217rhihqs83r5j5hene4b2jf6.apps.googleusercontent.com"


    Input_Dashboard = "ADMIN_DASHBOARD"
    Admin_History = "ADMIN_HISTORY"


    app = Flask(__name__)

    app.secret_key = "secret123" 

    @app.route("/google-auth", methods=["POST"])
    def login_g_auth():
        token = request.form["token"]
        try:
            google_account = id_token.verify_oauth2_token(token, requests.Request(), CLIENT_ID)
            
            # Store user info in session
            session['uid'] = google_account["sub"]
            session['email'] = google_account["email"]
            session['name'] = google_account.get("name", "User")

            db.collection("google_create_account").document(session['uid']).set({
                "uid": session['uid'],
                "email": session['email'],
                "name": session['name'],
                "provider": "google",
                "last_login": datetime.now(UTC).isoformat()
            }, merge=True)

            return redirect(url_for("admin_dashboard")) 
        except ValueError:
            return render_template("error.html", message="Invalid Google token")

    @app.route("/")
    def index():
        return render_template("admin_log_in.html")


    @app.route("/admin_dashboard", methods=['GET', 'POST'])
    def admin_dashboard():

        if request.method == "POST":
            Customer_Name = bleach.clean(request.form["CustomerName"])
            Admin_Vehicle = bleach.clean(request.form["Vehicle"])
            Admin_DriverS = bleach.clean(request.form["Driver"])
            uid = str(uuid.uuid4())

            try:
                db.collection("Input_Dashboard").document(uid).set({
                    "uid": uid,
                    "Customer_Name": Customer_Name,
                    "Admin_Vehicle": Admin_Vehicle,
                    "Admin_DriverS": Admin_DriverS,
                    "created_at": datetime.now(UTC).isoformat()
                })
            except Exception as e:
                print(e)

            return redirect(url_for("admin_dashboard"))  # refresh after insert

        # ✅ FETCH DATA HERE
        dashboard_ref = db.collection("Input_Dashboard")
        docs = dashboard_ref.stream()

        data = []
        for doc in docs:
            item = doc.to_dict()
            data.append({
                "Customer_Name": item.get("Customer_Name", ""),
                "Admin_Vehicle": item.get("Admin_Vehicle", ""),
                "Admin_DriverS": item.get("Admin_DriverS", ""),
                "created_at": item.get("created_at", "")

            })

        # ✅ PASS DATA TO TEMPLATE
        return render_template("admin_dashboard.html", Input_Dashboard=data)




    @app.route("/driver")
    def driver():
        return render_template("driver_side.html")


    if __name__ == "__main__":
        app.run(debug=True)

        #npm install firebase
        #npm install -g firebase-tools
        #pip install flask firebase-admin google-auth bleach werkzeug
        #https://console.firebase.google.com/project/water-distribution-b9a6b/firestore/databases/-default-/data?fb_gclid=CjwKCAiA2svIBhB-EiwARWDPjkvQoiqtd-H_y4dtaCSfMWwzK7ONcHUiFWepqqFXrqX-0LIDMRC6mhoCSqgQAvD_BwE
        