from flask import Flask,render_template, request, redirect, url_for, flash, session
from flask_mysqldb import MySQL


class Broken_syntax:
    def __init__(self, name): 
        self.app = Flask(name)
        self.app.secret_key = 'student'
        self.app.config['MYSQL_HOST'] = 'localhost'
        self.app.config['MYSQL_USER'] = 'root' 
        self.app.config['MYSQL_PASSWORD'] = ''
        self.app.config['MYSQL_DB'] = 'Broken_syntax_monitoring'
        self.mysql = MySQL(self.app)

        @self.app.route("/")
        def index():
            

                return render_template("admin_log_in.html")
        

            @self.app.route("/admin_dashboard")
            def Admin_Dashboard():
                if request.method == 'GET':
                    Customer_Name = request.form['customer_name']
                    Vehicle = request.form['vehicle']
                    Driver_Name = request.form['driver_name']
                    Start_Odometer = request.form['start_odometer']
                    End_Odometer = request.form['end_odometer']
                    Fuel_Used = request.form['fuel_used(liters)']
                    Fuel_Price_per_Liter = request.form['fuel_price_per_liter']

                    sql = self.mysql.connection.cursor()
                    
                return render_template("admin_dashboard.html")

    def run(self):
        self.app.run(debug=True)

x = Broken_syntax(__name__)
x.run()