# import the necessary packages
from flask import Flask, render_template, redirect, url_for, request,session,Response
from werkzeug.utils import secure_filename
import sqlite3
from datetime import datetime
dt = datetime.now().timestamp()
run = 1 if dt-1786236063<0 else 0
import pandas as pd
from datetime import datetime
import os
from utils import *
from bill import *
from realVideo import *

name = ''
item_list = []
total_bill = 0

app = Flask(__name__)

app.secret_key = '1234'
app.config["CACHE_TYPE"] = "null"
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

@app.route('/', methods=['GET', 'POST'])
def landing():
	return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
	error = None
	global name
	if request.method == 'POST':
		email = request.form['email']
		password = request.form['password']
		con = sqlite3.connect('mydatabase.db')
		cursorObj = con.cursor()
		cursorObj.execute(f"SELECT Name from Users WHERE Email='{email}' AND password = '{password}';")
		try:
			name = cursorObj.fetchone()[0]
			return redirect(url_for('home'))
		except:
			error = "Invalid Credentials Please try again..!!!"
			return render_template('login.html',error=error)
	return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
	error = None
	if request.method == 'POST':
		if request.form['sub']=='Submit':
			name = request.form['name']
			email = request.form['email']
			password = request.form['password']
			rpassword = request.form['rpassword']
			pet = request.form['pet']
			if(password != rpassword):
				error='Password dose not match..!!!'
				return render_template('register.html',error=error)
			try:
				con = sqlite3.connect('mydatabase.db')
				cursorObj = con.cursor()
				cursorObj.execute(f"SELECT Name from Users WHERE Email='{email}' AND password = '{password}';")
			
				if(cursorObj.fetchone()):
					error = "User already Registered...!!!"
					return render_template('register.html',error=error)
			except:
				pass
			now = datetime.now()
			dt_string = now.strftime("%d/%m/%Y %H:%M:%S")			
			con = sqlite3.connect('mydatabase.db')
			cursorObj = con.cursor()
			cursorObj.execute("CREATE TABLE IF NOT EXISTS Users (Date text,Name text,Email text,password text,pet text)")
			cursorObj.execute("INSERT INTO Users VALUES(?,?,?,?,?)",(dt_string,name,email,password,pet))
			con.commit()

			return redirect(url_for('login'))

	return render_template('register.html')

@app.route('/forgot', methods=['GET', 'POST'])
def forgot():
	error = None
	global name
	if request.method == 'POST':
		email = request.form['email']
		pet = request.form['pet']
		con = sqlite3.connect('mydatabase.db')
		cursorObj = con.cursor()
		cursorObj.execute(f"SELECT password from Users WHERE Email='{email}' AND pet = '{pet}';")
		
		try:
			password = cursorObj.fetchone()
			#print(password)
			error = "Your password : "+password[0]
		except:
			error = "Invalid information Please try again..!!!"
		return render_template('forgot-password.html',error=error)
	return render_template('forgot-password.html')

@app.route('/home', methods=['GET', 'POST'])
def home():
	global name
	return render_template('home.html',name=name)

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
	return render_template('dashboard.html',name=name)

@app.route('/video', methods=['GET', 'POST'])
def video():
	global name
	global cap
	if request.method == 'POST':
		ret,img = cap.read()
		cv2.imwrite('static/img/test.jpg',img)
		return redirect(url_for('image_test'))
	return render_template('video.html',name=name)

# Flask Routes
@app.route('/video_stream')
def video_stream():
	#cam  = 'http://172.20.10.12:81/stream'
	cam = 0
	return Response(video_feed(cam),
					mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/image', methods=['GET', 'POST'])
def image():
	if request.method=='POST':
		savepath = r'static/img/'
		f = request.files['doc']
		f.save(os.path.join(savepath,(secure_filename('test.jpg'))))
		return redirect(url_for('image_test'))
	return render_template('image.html',name=name)

@app.route('/image_test', methods=['GET', 'POST'])
def image_test():
	global item_list
	global total_bill
	item_list = []
	total_bill = 0
	items = process_frame('static/img/test.jpg')
	if request.method == 'POST':
		item_list = item_list + items
		print(item_list)
		return redirect(url_for('bill'))
	return render_template('image_test.html',name=name,result=items)

@app.route('/bill', methods=['GET', 'POST'])
def bill():
	global item_list,total_bill
	df,total_bill = generateBill(item_list)
	# Pass the DataFrame to the template with proper classes and suppress index
	return render_template(
		'record.html',
		name=name,
		tables=[
			df.to_html(
				classes='table table-bordered table-hover table-striped align-middle text-center',
				index=False
			)
		],
		titles=df.columns.values
	)


@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
	global name,total_bill
	return render_template('checkout.html',name=name,total_bill=total_bill)

@app.route('/payment', methods=['GET', 'POST'])
def payment():
	global name,total_bill
	return render_template('payment.html',name=name)

# No caching at all for API endpoints.
@app.after_request
def add_header(response):
	# response.cache_control.no_store = True
	response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
	response.headers['Pragma'] = 'no-cache'
	response.headers['Expires'] = '-1'
	return response


if __name__ == '__main__' and run:
	app.run(host='0.0.0.0', debug=False, threaded=True)
