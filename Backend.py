from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from cryptography.fernet import Fernet
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import datetime

import os

UPLOAD_FOLDER = 'static/images'

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}



def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
app = Flask(__name__)
app.config['SECRET_KEY'] = 'sdlllew'
##app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://En:******@localhost/mydatabase'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(50), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    payment_info = db.Column(db.String(255), nullable=False)
    is_seller = db.Column(db.Boolean, nullable=False, default=False)
    def set_password(self, new_password):
        self.password = new_password
    def check_password(self, password):
        return self.password == password

def get_current_user_id():
    if session.get('logged_in'):
        username = session['username']
        user = User.query.filter_by(username=username).first()
        if user:
            return user.id
    return None

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.Text, nullable=False)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    address = db.Column(db.String(255), nullable=False)
    payment_info = db.Column(db.String(255), nullable=False)

class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

with app.app_context():
    db.create_all()


@app.route('/')
def index():
    products = Product.query.all()
    return render_template('index.html', products=products)


@app.route('/products')
def display_products():
    products = Product.query.all()
    return render_template('index.html', products=products)


@app.route('/hello')
def hello_world():
    return 'Hello, World!'

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # 從表單中取得使用者的註冊資訊
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        address = request.form['address']
        payment_info = request.form['payment_info']
        
        # 在資料庫中創建一個新的使用者
        new_user = User(username=username, password=password, email=email, address=address, payment_info=payment_info)
        db.session.add(new_user)
        db.session.commit()
        return redirect('/')
    else:
        return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()
        if user is not None:
            # 如果查找到了該用戶，則設置一個 session 變數，以表示該用戶已經登入
            session['logged_in'] = True
            session['username'] = username
            is_seller = user.is_seller
            session['is_seller'] = is_seller

            flash('登入成功！')
            return redirect(url_for('index'))
        else:
            # 如果沒有找到該用戶，則顯示一條錯誤的消息
            flash('用戶名或密碼錯誤！')
    return render_template('login.html')

@app.route('/logout')
def logout():
    # 删除 session 中的登录信息
    session.pop('logged_in', None)
    session.pop('username', None)
    session.pop('is_seller', None)
    return redirect(url_for('index'))

@app.route('/member')
def member():
    # 確認用戶是否已經登入
    if not session.get('logged_in'):
        #flash('請先登入')
        return redirect(url_for('login'))
    # 獲取當前用戶的資訊
    user = User.query.filter_by(username=session['username']).first()
    # 渲染會員頁面模板並傳遞用戶資訊
    return render_template('member.html', user=user)

@app.route('/update_password', methods=['GET', 'POST'])
def update_password():
    # 確認用戶是否已經登入
    if not session.get('logged_in'):
        #flash('請先登入')
        return redirect(url_for('login'))
    # 獲取當前用戶的資訊
    user = User.query.filter_by(username=session['username']).first()
    if request.method == 'POST':
        # 從表單中取得新密碼和確認新密碼
        old_password = request.form['old_password']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        # 驗證舊密碼是否正確
        if not user.check_password(old_password):
            #flash('舊密碼不正確')
            return redirect(url_for('update_password'))
        # 驗證兩次輸入的密碼是否相同
        if password != confirm_password:
            #flash('兩次輸入的密碼不一致')
            return redirect(url_for('update_password'))
        # 更新使用者密碼
        user.set_password(password)
        db.session.commit()
        #flash('密碼修改成功')
        return redirect(url_for('index'))
    return render_template('update_password.html', user=user)



@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = request.form['price']
        
        # 從表單中獲取上傳的文件
        image_file = request.files['image']
        
        # 檢查是否有選擇文件
        if image_file and allowed_file(image_file.filename):


            now = datetime.datetime.now()
        

            filename = now.strftime('%Y%m%d%H%M%S') + '.' + secure_filename(image_file.filename)
        

            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            image_file.save(image_path)
            
            # 指定圖片的路徑
            product = Product(name=name, description=description, price=price, image_url=filename)
            

            db.session.add(product)
            db.session.commit()
            
            flash('商品刊登成功')
            return redirect(url_for('index'))
            
    return render_template('add_product.html')


@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    if session.get('logged_in'):
        user_id = get_current_user_id()
        product = Product.query.get(product_id)
        if product:
            cart_item = Cart.query.filter_by(user_id=user_id, product_id=product_id).first()
            if cart_item:
                cart_item.quantity += 1
            else:
                cart_item = Cart(user_id=user_id, product_id=product_id, quantity=1)
                db.session.add(cart_item)
            db.session.commit()
            flash('已將商品添加到購物車')
        else:
            flash('商品不存在')
    else:
        flash('請先登入')

    products = Product.query.all()  # 從資料庫中獲取所有商品列表
    return render_template('index.html', products=products)  # 替換成商品詳細頁面



@app.route('/cart')
def view_cart():
    if session.get('logged_in'):
        user_id = get_current_user_id()
        cart_items = Cart.query.filter_by(user_id=user_id).all()

        # 將每個購物車項目的商品信息關聯起來
        cart_with_products = []
        for cart_item in cart_items:
            product = Product.query.get(cart_item.product_id)
            if product:
                cart_with_products.append({
                    'cart_item': cart_item,
                    'product': product
                })

        return render_template('cart.html', cart_items=cart_with_products)
    else:
        flash('請先登入')
        return redirect(url_for('login'))


@app.route('/update_cart/<int:cart_item_id>', methods=['POST'])
def update_cart(cart_item_id):
    if session.get('logged_in'):
        new_quantity = int(request.form['new_quantity'])
        cart_item = Cart.query.get(cart_item_id)
        if cart_item:
            cart_item.quantity = new_quantity
            db.session.commit()
            flash('購物車內商品數量已更新')
        else:
            flash('購物車內商品不存在')
    else:
        flash('請先登入')
    return redirect(url_for('view_cart'))

@app.route('/users')
def users():
    users = User.query.all()
    return render_template('users.html', users=users)

if __name__ == '__main__':
    app.run()
