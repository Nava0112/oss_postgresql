import pytest
from oss import app
from unittest.mock import patch, MagicMock

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

# ---------------- Login Pages ----------------
def test_customer_login_page_loads(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'Login' in response.data or b'Customer' in response.data

def test_supplier_login_page_loads(client):
    response = client.get('/login_supplier')
    assert response.status_code == 200
    assert b'Login' in response.data or b'Supplier' in response.data

def test_admin_login_page_loads(client):
    response = client.get('/login_admin')
    assert response.status_code == 200
    assert b'Admin' in response.data

# ---------------- Invalid logins ----------------
@patch('oss.get_db_connection')
def test_invalid_customer_login(mock_conn, client):
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None
    mock_conn.return_value.cursor.return_value = mock_cursor

    response = client.post('/', data={'Username': 'fake', 'Password': 'fakepass'})
    assert b'Invalid' in response.data

@patch('oss.get_db_connection')
def test_invalid_supplier_login(mock_conn, client):
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None
    mock_conn.return_value.cursor.return_value = mock_cursor

    response = client.post('/login_supplier', data={'Username': 'bad', 'Password': 'badpass'})
    assert b'Invalid' in response.data

@patch('oss.get_db_connection')
def test_invalid_admin_login(mock_conn, client):
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None
    mock_conn.return_value.cursor.return_value = mock_cursor

    response = client.post('/login_admin', data={'AdminID': 'bad', 'AdminPassword': 'bad'})
    assert b'Invalid' in response.data

# ---------------- Valid logins & redirects ----------------
@patch('oss.get_db_connection')
def test_valid_customer_login_redirects(mock_conn, client):
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = (1,)
    mock_conn.return_value.cursor.return_value = mock_cursor

    response = client.post('/', data={'Username': 'john', 'Password': 'pass'})
    assert response.status_code == 302
    assert '/products' in response.headers['Location']

@patch('oss.get_db_connection')
def test_valid_supplier_login_redirects(mock_conn, client):
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = (2,)
    mock_conn.return_value.cursor.return_value = mock_cursor

    response = client.post('/login_supplier', data={'Username': 'sup', 'Password': 'pass'})
    assert response.status_code == 302
    assert '/supplier_products' in response.headers['Location']

@patch('oss.get_db_connection')
def test_valid_admin_login_redirects(mock_conn, client):
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = ('admin',)
    mock_conn.return_value.cursor.return_value = mock_cursor

    response = client.post('/login_admin', data={'AdminID': 'admin', 'AdminPassword': 'secret'})
    assert response.status_code == 302
    assert '/admin_home' in response.headers['Location']

# ---------------- Redirect protection ----------------
def test_customer_products_requires_login(client):
    response = client.get('/products')
    assert response.status_code == 302

def test_supplier_products_requires_login(client):
    response = client.get('/supplier_products')
    assert response.status_code == 302

def test_add_product_requires_supplier_login(client):
    response = client.get('/add_product_by_supplier')
    assert response.status_code == 302

# ---------------- Adding new records ----------------
def test_add_customer_form_loads(client):
    response = client.get('/add_customer')
    assert response.status_code == 200

def test_add_supplier_form_loads(client):
    response = client.get('/add_supplier')
    assert response.status_code == 200

@patch('oss.get_db_connection')
def test_submit_new_customer(mock_conn, client):
    mock_conn.return_value.cursor.return_value = MagicMock()
    response = client.post('/add_customer', data={
        'CustomerID': '10', 'CustomerName': 'Alice', 'Username': 'alice',
        'Password': 'pw', 'PhoneNumber': '12345', 'Email': 'alice@example.com',
        'Address': 'Wonderland'
    })
    assert response.status_code == 302
    assert '/' in response.headers['Location']

@patch('oss.get_db_connection')
def test_submit_new_supplier(mock_conn, client):
    mock_conn.return_value.cursor.return_value = MagicMock()
    response = client.post('/add_supplier', data={
        'SupplierID': '20', 'SupplierName': 'Bob', 'Username': 'bob',
        'Password': 'pw', 'PhoneNumber': '67890', 'Email': 'bob@example.com',
        'Address': 'Builderland'
    })
    assert response.status_code == 302
    assert '/add_product_by_supplier' in response.headers['Location']

# ---------------- Buying products ----------------
@patch('oss.get_db_connection')
def test_buy_product_flow(mock_conn, client):
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = (1, 'ProductX', 'Category', 100, 10)
    mock_conn.return_value.cursor.return_value = mock_cursor

    with client.session_transaction() as sess:
        sess['customer_id'] = '1'
    response = client.get('/buy_product/1')
    assert response.status_code == 200
    assert b'Product' in response.data

# ---------------- Viewing records ----------------
@patch('oss.get_db_connection')
def test_view_records_customers(mock_conn, client):
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [(1, 'John', '123', 'j@example.com', 'Earth')]
    mock_conn.return_value.cursor.return_value = mock_cursor

    response = client.get('/view_records/customers')
    assert response.status_code == 200
    assert b'John' in response.data

@patch('oss.get_db_connection')
def test_view_records_invalid_type(mock_conn, client):
    response = client.get('/view_records/unknown')
    assert response.status_code == 400

# ---------------- Logout ----------------
def test_logout_clears_session(client):
    with client.session_transaction() as sess:
        sess['customer_id'] = '1'
    response = client.get('/logout')
    assert response.status_code == 302
    assert '/' in response.headers['Location']
