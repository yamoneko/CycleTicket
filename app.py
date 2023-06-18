from flask import Flask,render_template,redirect,request,url_for,session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import LargeBinary,BINARY
from constant import price,adminname,adminpassword
import psycopg2
import base64
from PIL import Image
from io import BytesIO
from img2txt import extract_data,extract

app = Flask(__name__)

app.secret_key='ymk'

# database
app.config['SQLALCHEMY_DATABASE_URI']='postgresql://postgres:toor@localhost:5432/userData'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db=SQLAlchemy(app)
app.app_context().push()

#User table
class Users(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    username=db.Column(db.String(100),unique=True,nullable=False)
    password=db.Column(db.String(100))


#Orders table
class Orders(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    user_name = db.Column(db.String(100), nullable=False)
    tickets = db.Column(db.String(1000), nullable=False)
    image = db.Column(LargeBinary)
    verify = db.Column(db.String(50), nullable= True)

db.create_all()

#Home Page
@app.route("/")
def home():
    validUser = None
    tickets = []
    selected_ticket = []
    if session and session.get('username'):
        validUser = session['username']
        orders = Orders.query.all()
        if orders:
            for order in orders:
                pending_ticket = order.tickets.split(',')
                for i in pending_ticket:
                    selected_ticket.append(i)
        for i in range(1,101):
            tickets.append(f"{i:03}")
        return render_template('home.html', username=validUser, tickets=tickets, selected_ticket = selected_ticket)
    elif session and session['admin_username']:
        validUser = session['admin_username']
        return render_template('home.html', admin_name=validUser)
    return render_template('home.html')

    # if session and session.get('username'):
    #     tickets = []
    #     validUser = session['username']
    #     for i in range(1,101):
    #         tickets.append(f"{i:03}")
    #     return render_template('home.html', username=validUser, tickets=tickets)
    # return render_template('home.html')


# Admin route
@app.route('/admin')
def admin():
    orders = Orders.query.all()
    if session and session['admin_username']:
        valid_user = session['admin_username']
    order_tickets = []
    order_pending = []
    if orders:
        for order in orders:
            if order.image :
                file = BytesIO(order.image)
                image = Image.open(file)
                image_string_read = extract_data(image)
                order.image = base64.b64encode(order.image).decode('utf-8')
                if order.verify:
                    temp_dict = order.__dict__
                    temp_dict.update({"payment_info": image_string_read})
                    order_tickets.append(temp_dict)
                if not order.verify:
                    temp_dict = order.__dict__
                    temp_dict.update({"payment_info": image_string_read})
                    order_pending.append(temp_dict)
        return render_template('admin_dashboard.html',order_tickets = order_tickets,admin_name = valid_user, order_pending = order_pending)
    return render_template('admin.html')
    
    # order_list = Orders.query.all()
    # order_list_json = []
    # for order in order_list:
    #     if order.image:
    #         file = BytesIO(order.image)
    #         image = Image.open(file)
    #         image_string_read = extract_data(image)
    #         order.image = base64.b64encode(order.image).decode('utf-8')
    #         temp_dict = order.__dict__
    #         temp_dict.update({"payment_info": image_string_read})
    #         order_list_json.append(temp_dict)
    # return render_template("admin_dashboard.html", orders = order_list_json)


#Admin Logout
@app.route('/adminlogout')
def adminlogout():
    session.pop('admin_username',False)
    return redirect('/')

@app.route('/admin_accept/<int:orderid>')
def admin_accept(orderid):
    if orderid:
        data = Orders.query.get(orderid)
        data.verify = 'Accepted'
        db.session.commit()
        return redirect('/admin')
    return redirect('/')


@app.route('/admin_reject/<int:orderid>')
def admin_reject(orderid):
    if orderid:
        data = Orders.query.get(orderid)
        data.verify = "Rejected"
        db.session.commit()
        return redirect('/admin')
    return redirect('/')



#User Login
@app.route("/login", methods=['POST','GET'])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username == adminname and password == adminpassword:
            session['admin_username']= adminname
            return redirect('/admin')
        loginUser = Users.query.filter_by(username = username).first()
        if loginUser:
            session["username"] = loginUser.username
            return redirect('/')
    return render_template('login.html')


#User Register
@app.route("/register", methods=['POST','GET'])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        newUser = Users(username= username , password = password)
        db.session.add(newUser)
        db.session.commit()
        return redirect('/')
    return render_template('register.html')


#User Logout
@app.route("/logout")
def logout():
    session.pop('username', False)
    return redirect('/')


#Tickets Order
@app.route("/ticket_orders", methods=["POST"])
def ticket_order():
    form_selected_tickets = request.form.getlist("ticket[]")
    if len(form_selected_tickets):
        selected_ticket = ""
        for ticket in form_selected_tickets:
            if selected_ticket:
                selected_ticket +=","
            selected_ticket += ticket
        total = price * len(form_selected_tickets)
        if session and session["username"]:
            validUser = session["username"]
            user = Users.query.filter_by(username = validUser).first()
            validUserId = user.id
            if validUserId:
                newOrder = Orders(user_id=validUserId, user_name=validUser, tickets=selected_ticket )
                db.session.add(newOrder)
                db.session.commit()
                order_id = Orders.query.order_by(Orders.id.desc()).first()
                return render_template("order.html", tickets = form_selected_tickets, price=price, total=total, id=order_id.id)
            else:
                return redirect("/login")
        else:
            return redirect("/login")
    else:
        return redirect("/")


#Payment receive
@app.route('/update/<int:id>', methods=['POST'])
def update(id):
    if request.method == "POST":
        upload = request.files['img']
        up_img = upload.read()
        data = Orders.query.get(id)
        # data.image = up_img
        # db.session.commit()
        if data.image:
            data.image = up_img
            db.session.add(data)
        else:
            data.image = up_img
            db.session.commit()
        return redirect(url_for('check', checkid=id) )
    return redirect("/")


@app.route('/reupdate/<int:oid>' , methods=['POST'])
def reupdate(oid):
    if request.method == 'POST':
        image = request.files['img']
        upload_image = image.read()
        data = Orders.query.get(oid)
        if data.image:
            data.image = upload_image
            data.verify = None
            db.session.add(data)
            db.session.commit()
        else:
            data.image = upload_image
            db.session.commit()
        checkid = oid
        return redirect(url_for('check',checkid = checkid))
    return redirect('/')  


@app.route('/check/<int:checkid>',methods=['GET','POST'])
def check(checkid):
    if session and session['username']:
        validate_user = session['username']
        data = Orders.query.get(checkid)
        if not data.verify :
            return render_template('check.html',username = validate_user,checking = None)
        if data.verify == 'Rejected':
            pending_tickets = data.tickets.split(',')
            total_price = len(pending_tickets) * price
            orderId = checkid
            return render_template('order.html',username = validate_user, checking=data.verify, data = data, pending_tickets= pending_tickets, price = price,total_price = total_price, oid = orderId)
    return render_template('check.html',checking = data.verify)

#Show payment image
@app.route('/image/<int:id>')
def image(id):
    data = Orders.query.get(id)
    img = data.image
    img = base64.b64encode(img).decode('utf-8')
    return render_template('image.html', image_data = img)


@app.route('/userprofile')
def userprofile():
    if session and session['username']:
        valid_user = session['username']
        user = Users.query.filter_by(username=valid_user).first()
        my_order = Orders.query.filter_by(user_id=user.id).order_by(Orders.id.desc())
        orders = []
        for o in my_order:
            tem = o.__dict__
            tem['price'] = len(tem['tickets'].split(',')) * price
            orders.append(tem)
        return render_template('userprofile.html', orders=orders)
    return redirect('/')

#Main
if __name__ == '__main__':
    app.run(debug=True)