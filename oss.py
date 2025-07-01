from flask import Flask, render_template, request, redirect, url_for, session
import psycopg2
import os
from datetime import datetime
import apminsight
from dotenv import load_dotenv

load_dotenv()  # Load variables from .env

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Supabase PostgreSQL config
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")


def get_db_connection():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        sslmode='require'
    )

@app.route('/', methods=['GET', 'POST'])
def login_customer():
    if request.method == 'POST':
        username = request.form['Username']
        password = request.form['Password']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT CustomerID FROM Customers
            WHERE Username = %s AND Password = crypt(%s, Password)
        """, (username, password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if user:
            session['customer_id'] = user[0]
            return redirect(url_for('products'))
        else:
            return "Invalid credentials"
    return render_template('login_customer.html')


@app.route('/add_customer', methods=['GET', 'POST'])
def add_customer():
    if request.method == 'POST':
        data = (
            request.form['CustomerID'],
            request.form['CustomerName'],
            request.form['Username'],
            request.form['Password'],
            request.form['PhoneNumber'],
            request.form['Email'],
            request.form['Address']
        )
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Customers 
            (CustomerID, CustomerName, Username, Password, PhoneNumber, Email, Address)
            VALUES (%s, %s, %s, crypt(%s, gen_salt('bf')), %s, %s, %s)
        """, data)
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('login_customer'))
    return render_template('add_customer.html')


@app.route('/login_supplier', methods=['GET', 'POST'])
def login_supplier():
    if request.method == 'POST':
        username = request.form['Username']
        password = request.form['Password']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT SupplierID FROM Suppliers
            WHERE Username = %s AND Password = crypt(%s, Password)
        """, (username, password))
        supplier = cursor.fetchone()
        cursor.close()
        conn.close()
        if supplier:
            session['supplier_id'] = supplier[0]
            return redirect(url_for('supplier_products'))
        else:
            return "Invalid supplier credentials"
    return render_template('login_supplier.html')


@app.route('/add_supplier', methods=['GET', 'POST'])
def add_supplier():
    if request.method == 'POST':
        data = (
            request.form['SupplierID'],
            request.form['SupplierName'],
            request.form['Username'],
            request.form['Password'],
            request.form['PhoneNumber'],
            request.form['Email'],
            request.form['Address']
        )
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Suppliers 
            (SupplierID, SupplierName, Username, Password, PhoneNumber, Email, Address)
            VALUES (%s, %s, %s, crypt(%s, gen_salt('bf')), %s, %s, %s)
        """, data)
        conn.commit()
        cursor.close()
        conn.close()
        session['supplier_id'] = data[0]
        return redirect(url_for('add_product_by_supplier'))
    return render_template('add_supplier.html')


@app.route('/products')
def products():
    if 'customer_id' not in session:
        return redirect(url_for('login_customer'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Products")
    products = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('products.html', products=products)

@app.route('/buy_product/<int:product_id>', methods=['GET', 'POST'])
def buy_product(product_id):
    if 'customer_id' not in session:
        return redirect(url_for('login_customer'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Get the product details
    cursor.execute("SELECT * FROM Products WHERE ProductID = %s", (product_id,))
    product = cursor.fetchone()

    if not product:
        cursor.close()
        conn.close()
        return "Product not found", 404

    if request.method == 'POST':
        quantity = int(request.form['quantity'])

        available_stock = product[5]  # QuantityInStock
        if quantity > available_stock:
            cursor.close()
            conn.close()
            return f"Only {available_stock} items left in stock.", 400

        order_id = int(datetime.now().timestamp())
        total_price = product[4] * quantity

        # Insert into Orders
        cursor.execute("""
    INSERT INTO Orders (OrderID, CustomerID, ProductID, Order_Date, Quantity, TotalPrice)
    VALUES (%s, %s, %s, %s, %s, %s)
""", (order_id, session['customer_id'], product_id, datetime.now(), quantity, total_price))

        # Reduce the stock
        cursor.execute("""
            UPDATE Products
            SET QuantityInStock = QuantityInStock - %s
            WHERE ProductID = %s
        """, (quantity, product_id))

        conn.commit()
        cursor.close()
        conn.close()

        return render_template('order_confirmation.html', product=product, quantity=quantity, total_price=total_price)

    cursor.close()
    conn.close()
    return render_template('buy_product.html', product=product)



@app.route('/supplier_products')
def supplier_products():
    if 'supplier_id' not in session:
        return redirect(url_for('login_supplier'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Products WHERE SupplierID = %s", (session['supplier_id'],))
    products = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('supplier_products.html', products=products)

@app.route('/add_product_by_supplier', methods=['GET', 'POST'])
def add_product_by_supplier():
    if 'supplier_id' not in session:
        return redirect(url_for('login_supplier'))
    if request.method == 'POST':
        data = (
            request.form['ProductID'],
            request.form['ProductName'],
            session['supplier_id'],
            request.form['Category'],
            float(request.form['UnitPrice']),
            int(request.form['QuantityInStock'])
        )
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Products (ProductID, ProductName, SupplierID, Category, UnitPrice, QuantityInStock)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, data)
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('supplier_products'))
    return render_template('add_product_by_supplier.html')

@app.route('/view_records/<record_type>')
def view_records(record_type):
    conn = get_db_connection()
    cursor = conn.cursor()

    if record_type == 'customers':
        cursor.execute("""
            SELECT CustomerID, CustomerName, PhoneNumber, Email, Address
            FROM Customers
        """)
        records = cursor.fetchall()
        headers = ['CustomerID', 'CustomerName', 'PhoneNumber', 'Email', 'Address']

    elif record_type == 'suppliers':
        cursor.execute("""
            SELECT SupplierID, SupplierName, PhoneNumber, Email, Address
            FROM Suppliers
        """)
        records = cursor.fetchall()
        headers = ['SupplierID', 'SupplierName', 'PhoneNumber', 'Email', 'Address']

    elif record_type == 'products':
        cursor.execute("SELECT * FROM Products")
        records = cursor.fetchall()
        headers = ['ProductID', 'ProductName', 'SupplierID', 'Category', 'UnitPrice', 'QuantityInStock']

    else:
        cursor.close()
        conn.close()
        return "Invalid record type", 400

    cursor.close()
    conn.close()

    return render_template('view_records.html', record_type=record_type.title(), headers=headers, records=records)

@app.route('/admin_home')
def admin_home():
    return render_template('admin_home.html')

@app.route('/login_admin', methods=['GET', 'POST'])
def login_admin():
    if request.method == 'POST':
        admin_id = request.form['AdminID']
        admin_pass = request.form['AdminPassword']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM Admins 
            WHERE AdminID = %s AND AdminPassword = %s
        """, (admin_id, admin_pass))
        admin = cursor.fetchone()
        cursor.close()
        conn.close()

        if admin:
            session['admin'] = True
            session['admin_id'] = admin_id
            return redirect(url_for('admin_home'))
        else:
            return "Invalid admin credentials"
    return render_template('login_admin.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_customer'))

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
