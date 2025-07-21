from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from pymongo import MongoClient
import os
from bson.objectid import ObjectId
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
from datetime import datetime
from ml.recommend import recommend_products
from ml.anomaly import detect_anomalies
from ml.price_opt import optimize_price
from ml.inventory_opt import optimize_inventory
import qrcode
import base64
from io import BytesIO

app = Flask(__name__)
CORS(app)
app.secret_key = 'your_secret_key_here'

# MongoDB connection
MONGO_URI = "mongodb+srv://aryanzeal22105:19DKatRulmvelMCN@shadow.giscmli.mongodb.net/inventory_management?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client['inventory_management']
products = db['products']
users = db['users']
bills = db['bills']
inventory = db['inventory']

@app.route('/')
def index():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    return render_template('index.html')


# ---------- PRODUCT MANAGEMENT ----------

@app.route('/products')
def products_page():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    all_products = list(db.products.find())
    for product in all_products:
        product['_id'] = str(product['_id'])
    return render_template('products.html', products=all_products)


@app.route('/product/add', methods=['POST'])
def add_product():
    name = request.form.get('name')
    category = request.form.get('category')
    price = request.form.get('price')
    stock = request.form.get('stock')

    if not name or not category or price is None or stock is None:
        # Optionally, flash an error or handle gracefully
        return redirect(url_for('products_page'))

    try:
        price = float(price)
        stock = int(stock)
    except ValueError:
        # Handle invalid input
        return redirect(url_for('products_page'))

    db.products.insert_one({
        'name': name,
        'category': category,
        'price': price,
        'stock': stock
    })
    return redirect(url_for('products_page'))


@app.route('/product/edit/<product_id>', methods=['POST'])
def edit_product(product_id):
    # TODO: Implement update logic from form
    return redirect(url_for('products_page'))


@app.route('/product/delete/<product_id>', methods=['POST'])
def delete_product(product_id):
    db.products.delete_one({'_id': ObjectId(product_id)})
    return redirect(url_for('products_page'))

@app.route('/update_product/<product_id>', methods=['POST'])
def update_product(product_id):
    name = request.form.get('name')
    category = request.form.get('category')
    price = request.form.get('price')
    if not name or not category or price is None:
        return redirect(url_for('products_page'))  # Adjust based on your existing route
    try:
        price = float(price)
    except ValueError:
        return redirect(url_for('products_page'))
    products.update_one(
        {"_id": ObjectId(product_id)},
        {"$set": {"name": name, "category": category, "price": price}}
    )
    return redirect(url_for('products_page'))  # Adjust based on your existing route


# ---------- INVENTORY MANAGEMENT ----------

@app.route('/inventory')
def inventory():
    if not session.get('user_id'):
        return redirect(url_for('login'))

    products = list(db.products.find())
    for product in products:
        product['_id'] = str(product['_id'])

    return render_template('inventory.html', products=products)


@app.route('/inventory/update', methods=['POST'])
def inventory_update_universal():
    product_id = request.form.get('product_id')
    quantity = request.form.get('quantity')
    if not product_id or quantity is None:
        return jsonify({"error": "Missing product or quantity"}), 400
    try:
        quantity = int(quantity)
    except ValueError:
        return jsonify({"error": "Invalid quantity"}), 400
    product = products.find_one({"_id": ObjectId(product_id)})
    if not product:
        return jsonify({"error": "Product not found"}), 404
    new_stock = product['stock'] + quantity
    if new_stock < 0:
        return jsonify({"error": "Insufficient stock"}), 400
    products.update_one(
        {"_id": ObjectId(product_id)},
        {"$set": {"stock": new_stock}}
    )
    return jsonify({"message": "Stock updated!", "new_stock": new_stock})


# ---------- BILLING SYSTEM ----------

@app.route('/billing', methods=['POST'])
def billing():
    data = request.get_json()
    if not data or 'items' not in data or not data['items']:
        return jsonify({"error": "No items provided"}), 400

    items = data['items']
    payment_method = data.get('payment_method', 'cash')
    bill_summary = []
    total = 0
    for item in items:
        product_id = item.get('productId')
        quantity = int(item.get('quantity', 0))
        product = products.find_one({"_id": ObjectId(product_id)})
        if not product or product['stock'] < quantity:
            return jsonify({"error": f"Insufficient stock for {product['name'] if product else 'Unknown'}"}), 400
        # Update stock
        new_stock = product['stock'] - quantity
        products.update_one(
            {"_id": ObjectId(product_id)},
            {"$inc": {"stock": -quantity}}
        )
        # Remove product if stock is now zero
        if new_stock == 0:
            products.delete_one({"_id": ObjectId(product_id)})
        item_total = product['price'] * quantity
        total += item_total
        bill_summary.append({
            "product_id": product_id,
            "product_name": product["name"],
            "quantity": quantity,
            "price_per_unit": product["price"],
            "total": item_total
        })

    # Generate payment info and QR code for the total bill if online
    qr_code_base64 = None
    payment_info = f"Pay ₹{total} for your purchase"
    if payment_method == 'online':
        qr = qrcode.make(payment_info)
        buffered = BytesIO()
        qr.save(buffered, format="PNG")
        qr_code_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

    # Save bill in MongoDB
    bills.insert_one({
        "items": bill_summary,
        "total": total,
        "timestamp": datetime.now(),
        "user_id": session.get("user_id"),
        "payment_method": payment_method,
        "payment_info": payment_info,
        "qr_code_base64": qr_code_base64
    })

    return jsonify({
        "message": "Billing successful!",
        "total": total,
        "qr_code_base64": qr_code_base64,
        "items": bill_summary
    })


# ---------- ML ENDPOINTS ----------

@app.route('/ml/demand_forecast')
def demand_forecast():
    return jsonify({'forecast': []})  # Add model logic later


@app.route('/ml/recommend')
def recommend():
    user_history = []  # Replace with actual user history
    result = recommend_products(user_history)
    return jsonify({'recommendations': result})


@app.route('/ml/anomaly')
def anomaly():
    data = []  # Replace with real data
    result = detect_anomalies(data)
    return jsonify({'anomalies': result})


@app.route('/ml/price_opt')
def price_opt():
    sales_data = []
    market_data = []
    result = optimize_price(sales_data, market_data)
    return jsonify({'optimal_prices': result})


@app.route('/ml/inventory_opt')
def inventory_opt():
    inventory_data = []
    sales_data = []
    result = optimize_inventory(inventory_data, sales_data)
    return jsonify({'optimal_inventory': result})


# ---------- USER AUTH ----------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            return render_template('login.html', error='Please enter both username and password.')
        user = db.users.find_one({'username': username})
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user.get('userID', str(user['_id']))
            return redirect(url_for('index'))
        return render_template('login.html', error='Invalid credentials.')
    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            return render_template('signup.html', error='Please enter both username and password.')
        if db.users.find_one({'username': username}):
            return render_template('signup.html', error='Username already exists.')
        user_id_str = str(uuid.uuid4())
        db.users.insert_one({
            'username': username,
            'password': generate_password_hash(password),
            'userID': user_id_str
        })
        return redirect(url_for('login', message='Registration successful!'))
    return render_template('signup.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))


# ---------- PRODUCT API ----------

@app.route('/api/products', methods=['GET'])
def api_get_products():
    products = list(db.products.find())
    for p in products:
        p['_id'] = str(p['_id'])
    return jsonify(products)


@app.route('/api/products', methods=['POST'])
def api_add_product():
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    product = {
        'name': data.get('name'),
        'category': data.get('category'),
        'price': float(data.get('price', 0)),
        'stock': int(data.get('stock', 0))
    }
    result = db.products.insert_one(product)
    product['_id'] = str(result.inserted_id)
    return jsonify(product), 201


@app.route('/api/products/<product_id>', methods=['PUT'])
def api_update_product(product_id):
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    update = {k: data[k] for k in ['name', 'category', 'price', 'stock'] if k in data}
    if 'price' in update:
        update['price'] = float(update['price'])
    if 'stock' in update:
        update['stock'] = int(update['stock'])
    result = db.products.update_one({'_id': ObjectId(product_id)}, {'$set': update})
    if result.matched_count == 0:
        return jsonify({'error': 'Product not found'}), 404
    product = db.products.find_one({'_id': ObjectId(product_id)})
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    product['_id'] = str(product['_id'])
    return jsonify(product)


@app.route('/api/products/<product_id>', methods=['DELETE'])
def api_delete_product(product_id):
    result = db.products.delete_one({'_id': ObjectId(product_id)})
    if result.deleted_count == 0:
        return jsonify({'error': 'Product not found'}), 404
    return jsonify({'success': True})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
