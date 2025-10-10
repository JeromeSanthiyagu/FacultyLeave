# importing libraries
from flask import Flask, render_template, url_for, request, redirect, flash
from flask_mysqldb import MySQL
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os

# creating flask application
app=Flask(__name__) 
app.secret_key='flash message'

#config database
import os

app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST', 'mysql-faculty-leave.mysql.database.azure.com')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER', 'facultyadmin')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD', 'Jerom@2004')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB', 'faculty_leave')
app.config['MYSQL_PORT'] = int(os.getenv('MYSQL_PORT', 3306))
app.config['MYSQL_SSL_CA'] = '/etc/ssl/certs/ca-certificates.crt'



mysql=MySQL(app)

# SMTP mail credentials
SMTP_SENDER = os.getenv('SMTP_SENDER', 'miniprojectteam.12@gmail.com')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')


# home page
@app.route("/")
def index():
    return render_template("index.html")

# login function
@app.route('/login', methods=['POST'])
def login():
    if request.method=='POST':
        cursor=mysql.connection.cursor()
        id_num=request.form['id_num']
        password=request.form['password']
        cursor.execute("SELECT * FROM faculty WHERE id_num=%s",(id_num,))
        data=cursor.fetchone()
        if(data and data[4]==password):
            cursor.execute("SELECT num,id_num,from_date,to_date,reason,status FROM leave_application WHERE status='c' or status='b'  ORDER BY num DESC")
            applications=cursor.fetchall()
            cursor.close()
            return render_template("index.html", faculty=[data], applications=applications)
        cursor.execute("SELECT * FROM student_details WHERE id_num=%s",(id_num,))
        data=cursor.fetchone()
        cursor.close()
        if(data and data[4]==password):
            return render_template("index.html", student=[data])
        else:
            flash("Incorrect password!")
            return render_template("index.html", error="incorrect_login_password")

# registration function
@app.route("/register",methods=['POST'])
def register():
    if request.method=="POST":
        id_num=request.form['id_num']
        name=request.form['name']
        email=request.form['email']
        phone=request.form['phone']
        password=request.form['password']
        conf_password=request.form['confirm_password']

        if(password!=conf_password):
            flash("Unmatched passwords!")
            return render_template("index.html", data=[id_num,name,email,phone,password],
                                   error="umatched_password1")
        cursor=mysql.connection.cursor()
        try:
            cursor.execute("INSERT INTO student_details VALUES (%s,%s,%s,%s,%s)",(id_num,name,email,phone,password))
        except Exception as e:
            flash(e)
        mysql.connection.commit()
        cursor.close()
        flash("Registration successful!")
        return redirect(url_for('index'))
    
# password reset function
@app.route("/reset", methods=['POST'])
def reset():
    if request.method=="POST":
        id_num=request.form['id_num']
        name=request.form['name']
        email=request.form['email']
        phone=request.form['phone']
        password=request.form['password']
        conf_password=request.form['confirm_password']

        cursor=mysql.connection.cursor()
        cursor.execute("SELECT * FROM student_details WHERE id_num=%s and name=%s and email=%s and phone=%s",(id_num,name,email,phone))
        data=cursor.fetchone()
        if(data):
            cursor.execute('UPDATE student_details SET password=%s WHERE id_num=%s',(password,id_num))
            mysql.connection.commit()
            cursor.close()
            flash("Reset successful!")
            return render_template('index.html')
        else:
            flash("Unmatched details!")
            return render_template('index.html', error="unmatched")

# leave application function     
@app.route('/apply_leave', methods=['POST'])
def apply_leave():
    if request.method=='POST':
        id_num=request.form['id_num']
        from_date=request.form['from_date']
        to_date=request.form['to_date']
        reason=request.form['reason']

        cursor=mysql.connection.cursor()
        cursor.execute("INSERT INTO leave_application(id_num,from_date,to_date,reason) VALUES (%s,%s,%s,%s)",(id_num,from_date,to_date,reason))
        mysql.connection.commit()
        flash("Applied successfully!")
        return render_template('index.html', student=[[id_num]])

# application dashboard function 
@app.route("/history", methods=['POST'])
def history():
    if request.method=='POST':
        id_num=request.form['id_num']
        
        cursor=mysql.connection.cursor()
        cursor.execute("SELECT * FROM leave_application WHERE id_num=%s ORDER BY num DESC",(id_num,))
        data=cursor.fetchall()
        cursor.close()

        return render_template('index.html', student=[[id_num,'checked']], previous=data)
    
@app.route("/student_history", methods=['POST'])
def student_history():
    if request.method=='POST':
        id_num=request.form['id_num']
        fac_id_num= request.form['fac_id_num']

        cursor=mysql.connection.cursor()
        cursor.execute("SELECT * FROM leave_application WHERE id_num=%s ORDER BY num DESC",(id_num,))
        student=cursor.fetchall()
        cursor.close()

        cursor=mysql.connection.cursor()
        cursor.execute("SELECT * FROM faculty WHERE id_num=%s",(fac_id_num,))
        data=cursor.fetchone()
        cursor.execute("SELECT num,id_num,from_date,to_date,reason,status FROM leave_application WHERE status='c'")
        applications=cursor.fetchall()

        return render_template("index.html", heading=str(id_num), faculty=[data], applications=applications, student_data= student) 

# application delete function
@app.route("/delete", methods=['POST'])
def delete():
    if request.method=='POST':
        num=request.form['num']
        id_num=request.form['id_num']

        cursor=mysql.connection.cursor()
        cursor.execute("DELETE FROM leave_application WHERE num=%s",(num,))
        mysql.connection.commit()
        flash("Deleted successfully!")

        cursor.execute("SELECT * FROM leave_application WHERE id_num=%s",(id_num,))
        data=cursor.fetchall()
        cursor.close()
        return render_template('index.html', student=[[id_num,'checked']], previous=data)

# leave grant function  
# leave grant function
@app.route('/grant', methods=["POST"])
def grant():
    if request.method == 'POST':
        # NOTE: 'num' is the application number used for UPDATE/SELECT
        app_num = request.form['num'] 
        fac_id_num = request.form['fac_id_num']
        hod = request.form['hod']
        comment = request.form['comment']
        flag = request.form['flag'] # Status flag for email subject

        cursor = mysql.connection.cursor()
        
        # 1. Insert comment (using app_num, which is 'num')
        cursor.execute("INSERT INTO comments VALUES (%s,%s)", (app_num, comment))

        # 2. Update status based on HoD status
        if hod == 'n':
            # Update status to 'b' (Passed to HoD)
            cursor.execute("UPDATE leave_application SET status='b' WHERE num=%s", (app_num,))
            flash("Leave passed to HoD!")

        if hod == 'y':
            # Update status to 'a' (Approved)
            cursor.execute("UPDATE leave_application SET status='a' WHERE num=%s", (app_num,))
            flash("Leave approved!")
        
        # COMMIT all database changes together
        mysql.connection.commit()
        
        # 3. Fetch data for faculty dashboard refresh
        cursor.execute("SELECT * FROM faculty WHERE id_num=%s", (fac_id_num,))
        data = cursor.fetchone()
        
        # Select pending applications for dashboard refresh
        cursor.execute("SELECT num,id_num,from_date,to_date,reason,status FROM leave_application WHERE status='c' or status='b'")
        applications = cursor.fetchall()
        
        # 4. Email setup and send
        # Get student email using the application number
        cursor.execute("SELECT T1.email FROM student_details AS T1 JOIN leave_application AS T2 ON T1.id_num = T2.id_num WHERE T2.num=%s", (app_num,))
        receiver = cursor.fetchone()[0]
        
        email_body = f"<html><body><b><h1 style='color:green;'>Leave {flag} !</h1></b><br><h2 style='color:blue;'>{comment}</h2></body></html>"
        message = MIMEMultipart('alternative', None, [MIMEText(email_body, 'html')])
        message['Subject'] = "Leave Status"
        message['From'] = sender
        message['To'] = receiver
        
        try:
            server = smtplib.SMTP('smtp.gmail.com:587')
            server.ehlo()
            server.starttls()
            server.login(sender, psswd)
            server.sendmail(sender, receiver, message.as_string())
            server.quit()
        except Exception as e:
            print(f"Exception occurred during email send: {e}")
            
        cursor.close()
        return render_template("index.html", faculty=[data], applications=applications)

# leave deny function
@app.route("/deny", methods=["POST"])
def deny():
    if request.method == 'POST':
        # NOTE: 'num' is the application number used for UPDATE/SELECT
        app_num = request.form['num'] 
        fac_id_num = request.form['fac_id_num']
        comment = request.form['comment']
        flag = request.form['flag'] # Status flag for email subject

        cursor = mysql.connection.cursor()
        
        # 1. Insert comment
        cursor.execute("INSERT INTO comments VALUES (%s,%s)", (app_num, comment))
        
        # 2. Update status to 'r' (Rejected)
        cursor.execute("UPDATE leave_application SET status='r' WHERE num=%s", (app_num,))
        
        # COMMIT all database changes together
        mysql.connection.commit()
        flash("Leave rejected!")
        
        # 3. Fetch data for faculty dashboard refresh
        cursor.execute("SELECT * FROM faculty WHERE id_num=%s", (fac_id_num,))
        data = cursor.fetchone()
        
        # Select pending applications for dashboard refresh
        cursor.execute("SELECT num,id_num,from_date,to_date,reason,status FROM leave_application WHERE status='c' or status='b'")
        applications = cursor.fetchall()

        # 4. Email setup and send
        # Get student email using the application number
        cursor.execute("SELECT T1.email FROM student_details AS T1 JOIN leave_application AS T2 ON T1.id_num = T2.id_num WHERE T2.num=%s", (app_num,))
        receiver = cursor.fetchone()[0]

        email_body = f"<html><body><b><h1 style='color:red;'>Leave {flag}!</b><br><h2 style='color:blue;'>{comment}</h2></body></html>"
        message = MIMEMultipart('alternative', None, [MIMEText(email_body, 'html')])
        message['Subject'] = "Leave Status"
        message['From'] = sender
        message['To'] = receiver
        
        try:
            server = smtplib.SMTP('smtp.gmail.com:587')
            server.ehlo()
            server.starttls()
            server.login(sender, psswd)
            server.sendmail(sender, receiver, message.as_string())
            server.quit()
        except Exception as e:
            print(f"Exception occurred during email send: {e}")
            
        cursor.close()
        return render_template("index.html", faculty=[data], applications=applications)

if __name__=="__main__":
    app.run(debug=True) # running the appplication
