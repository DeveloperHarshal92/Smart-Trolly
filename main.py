# import the necessary packages
from dotenv import load_dotenv
load_dotenv()
from flask import Flask, render_template, redirect, url_for, request,session,Response
import uuid
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
from payment import create_order, verify_payment
from email_service import send_bill_email

name = ''
item_list = []
total_bill = 0

def _get_trolley_id() -> str:
	"""
	Returns this browser session's trolley_id, creating one in the
	Flask session cookie on first use. The actual cart state lives in
	realVideo.CART_STORE (server-side, in-memory) — this cookie value
	is only the lookup key. See realVideo.py CART_STORE docstring for why.
	"""
	if 'trolley_id' not in session:
		session['trolley_id'] = str(uuid.uuid4())
	return session['trolley_id']

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
    trolley_id = _get_trolley_id()
    if request.method == 'POST':
        from realVideo import capture_frame
        trolley_id = _get_trolley_id()
        success = capture_frame('static/img/test.jpg', trolley_id=trolley_id)
        if not success:
            # Camera unavailable — show an error instead of silently breaking
            return render_template('video.html', name=name,
                                   error="Camera not available or frame could not be captured.")
        return redirect(url_for('image_test'))
    return render_template('video.html', name=name)


@app.route('/video_stream')
def video_stream():
    from realVideo import video_feed
    trolley_id = _get_trolley_id()
    return Response(
        video_feed(trolley_id),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@app.route('/auto_scan', methods=['POST'])
def auto_scan():
    """
    Polled by the frontend every ~2s once the user clicks
    "Capture & detect" on the live feed. Reads the current frame
    in-memory (no manual capture needed), runs detection, and
    appends any newly detected items to this trolley's cart.

    Returns JSON: {status, new_items, all_items} so the frontend
    can play a beep per new item and update the live list without
    a page reload.
    """
    from realVideo import detect_live_frame
    trolley_id = _get_trolley_id()
    result = detect_live_frame(trolley_id=trolley_id)
    return result


@app.route('/reset_scan', methods=['POST'])
def reset_scan():
    """Clears this trolley's cart — called when starting a fresh auto-scan session."""
    from realVideo import set_cart_items
    trolley_id = _get_trolley_id()
    set_cart_items(trolley_id, [])
    return {"status": "ok"}

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
	from realVideo import get_cart_items
	trolley_id = _get_trolley_id()
	items = get_cart_items(trolley_id)
	if request.method == 'POST':
		print(items)
		return redirect(url_for('bill'))
	return render_template('image_test.html',name=name,result=items)

@app.route('/bill', methods=['GET', 'POST'])
def bill():
	from realVideo import get_cart_items
	global item_list, total_bill
	trolley_id = _get_trolley_id()
	item_list = get_cart_items(trolley_id)
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

@app.route('/payment', methods=['GET', 'POST'])
def payment():
	# All payments must start at checkout so a Razorpay order is created first.
	return redirect(url_for('checkout'))

# No caching at all for API endpoints.
@app.after_request
def add_header(response):
	# response.cache_control.no_store = True
	response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
	response.headers['Pragma'] = 'no-cache'
	response.headers['Expires'] = '-1'
	return response

# ─────────────────────────────────────────────────────────────────────────────
# /checkout  — shows total + asks for email, triggers Razorpay order creation
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    global name, total_bill, item_list
    from realVideo import get_cart_items

    # The real cart always controls whether payment is allowed. A labelled demo
    # invoice keeps the UI useful before the first camera scan.
    item_list = get_cart_items(_get_trolley_id())
    is_demo_invoice = not bool(item_list)
    display_items = item_list or (
        ['parle_g'] * 3 + ['good_day'] * 2 + ['colgate']
    )
    invoice = build_invoice_summary(display_items)
    total_bill = invoice['grand_total']
    customer_email = request.form.get('email', '').strip()

    template_context = {
        'name': name,
        'total_bill': total_bill,
        'invoice': invoice,
        'is_demo_invoice': is_demo_invoice,
        'customer_email': customer_email,
    }

    if request.method == 'POST':
        if is_demo_invoice:
            return render_template(
                'checkout.html', **template_context,
                error="Your trolley is empty. Scan at least one product before checkout.",
            )
        if not customer_email:
            return render_template(
                'checkout.html', **template_context,
                error="Please enter your email to receive the invoice.",
            )

        try:
            receipt_id = f"trolley_{uuid.uuid4().hex[:24]}"
            order = create_order(total_bill, receipt_id=receipt_id)
        except Exception as exc:
            app.logger.exception("Could not create Razorpay order")
            error = (str(exc) if isinstance(exc, EnvironmentError)
                     else "Unable to connect to Razorpay. Please try again.")
            return render_template(
                'checkout.html', **template_context, error=error,
            )

        # Save the exact cart snapshot being paid for. The live trolley may
        # change while the Razorpay window is open.
        session['razorpay_order_id'] = order['id']
        session['customer_email'] = customer_email
        session['checkout_items'] = item_list
        session['checkout_total'] = total_bill

        return render_template(
            'payment.html',
            name=name,
            total_bill=total_bill,
            razorpay_key=os.environ.get("RAZORPAY_KEY_ID", ""),
            order_id=order['id'],
            amount_paise=order['amount'],
            customer_email=customer_email,
        )

    return render_template('checkout.html', **template_context)


@app.route('/clear_cart', methods=['POST'])
def clear_cart():
    from realVideo import set_cart_items

    set_cart_items(_get_trolley_id(), [])
    for key in ('razorpay_order_id', 'customer_email',
                'checkout_items', 'checkout_total'):
        session.pop(key, None)
    return redirect(url_for('checkout'))

# ─────────────────────────────────────────────────────────────────────────────
# /payment_callback  — verify Razorpay response, generate PDF, then email bill
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/payment_callback', methods=['POST'])
def payment_callback():
    razorpay_order_id = request.form.get('razorpay_order_id')
    razorpay_payment_id = request.form.get('razorpay_payment_id')
    razorpay_signature = request.form.get('razorpay_signature')

    # Reject a payment from another checkout session before signature checking.
    if not razorpay_order_id or razorpay_order_id != session.get('razorpay_order_id'):
        return render_template(
            'payment_failed.html', name=name,
            reason="Order ID mismatch. Payment was not confirmed.",
        )

    if not all((razorpay_payment_id, razorpay_signature)):
        return render_template(
            'payment_failed.html', name=name,
            reason="Razorpay did not return complete payment details.",
        )

    if not verify_payment(razorpay_order_id, razorpay_payment_id, razorpay_signature):
        return render_template(
            'payment_failed.html', name=name,
            reason="Signature verification failed. Payment was not confirmed.",
        )

    # Generate and email the immutable cart snapshot that was paid for.
    customer_email = session.get('customer_email', '')
    checkout_items = session.get('checkout_items', [])
    checkout_total = session.get('checkout_total', 0)
    pdf_filename = None

    try:
        pdf_path = generateBillPDF(
            checkout_items, customer_name=name, customer_email=customer_email
        )
        pdf_filename = os.path.basename(pdf_path)
        email_result = send_bill_email(
            recipient_email=customer_email,
            customer_name=name,
            total_bill=checkout_total,
            pdf_path=pdf_path,
        )
    except Exception:
        app.logger.exception("Payment succeeded, but invoice processing failed")
        email_result = {
            'success': False,
            'message': "Payment succeeded, but the invoice could not be generated or emailed.",
        }

    for key in ('razorpay_order_id', 'customer_email',
                'checkout_items', 'checkout_total'):
        session.pop(key, None)

    return render_template(
        'payment_success.html',
        name=name,
        total_bill=checkout_total,
        payment_id=razorpay_payment_id,
        email_sent=email_result['success'],
        email_msg=email_result['message'],
        pdf_filename=pdf_filename,
    )

# ─────────────────────────────────────────────────────────────────────────────
# /download_bill/<filename>  — lets user re-download their PDF from browser
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/download_bill/<filename>')
def download_bill(filename):
    from flask import send_from_directory
    bills_dir = os.path.join(app.root_path, 'static', 'bills')
    return send_from_directory(bills_dir, filename, as_attachment=True)


@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html', name=name), 404


if __name__ == '__main__' and run:
	app.run(host='0.0.0.0', debug=False, threaded=True)