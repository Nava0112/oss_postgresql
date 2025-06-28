import pytest
from oss import app
from unittest.mock import patch, MagicMock
from flask import session

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_customer_login_page_loads(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'Customer' in response.data or b'Login' in response.data

def test_supplier_login_page_loads(client):
    response = client.get('/login_supplier')
    assert response.status_code == 200
    assert b'Supplier' in response.data or b'Login' in response.data

def test_redirect_if_not_logged_in(client):
    response = client.get('/products', follow_redirects=False)
    assert response.status_code == 302
    assert '/' in response.headers['Location']

@patch('oss.get_db_connection')
def test_invalid_customer_login(mock_conn, client):
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None
    mock_conn.return_value.cursor.return_value = mock_cursor

    response = client.post('/', data={
        'CustomerID': '999',
        'CustomerName': 'fakeuser'
    }, follow_redirects=True)
    assert b'Invalid' in response.data

@patch('oss.get_db_connection')
def test_products_page_redirect(mock_conn, client):
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = []
    mock_conn.return_value.cursor.return_value = mock_cursor

    response = client.get('/products', follow_redirects=False)
    assert response.status_code == 302

def test_add_customer_form_loads(client):
    response = client.get('/add_customer')
    assert response.status_code == 200

# ---------------- Additional Test Cases ----------------
@patch('oss.get_db_connection')
def test_valid_customer_login(mock_conn, client):
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = (1,)
    mock_conn.return_value.cursor.return_value = mock_cursor

    response = client.post('/', data={'CustomerID': '1', 'CustomerName': 'John'})
    assert response.status_code == 302

@patch('oss.get_db_connection')
def test_add_customer_submission(mock_conn, client):
    mock_conn.return_value.cursor.return_value = MagicMock()

    response = client.post('/add_customer', data={
        'CustomerID': '10', 'CustomerName': 'Alice', 'PhoneNumber': '12345',
        'Email': 'alice@example.com', 'Address': 'Wonderland'})
    assert response.status_code == 302

@patch('oss.get_db_connection')
def test_sql_injection_login(mock_conn, client):
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None
    mock_conn.return_value.cursor.return_value = mock_cursor

    response = client.post('/', data={'CustomerID': "' OR '1'='1", 'CustomerName': 'admin'})
    assert b"Invalid customer credentials" in response.data

def test_unauthenticated_supplier_redirect(client):
    response = client.get('/supplier_products')
    assert response.status_code == 302

def test_logout_clears_session(client):
    with client.session_transaction() as sess:
        sess['customer_id'] = '1'
    response = client.get('/logout')
    assert response.status_code == 302

@patch('oss.get_db_connection')
def test_empty_fields_login(mock_conn, client):
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None
    mock_conn.return_value.cursor.return_value = mock_cursor

    response = client.post('/', data={'CustomerID': '', 'CustomerName': ''})
    assert b"Invalid" in response.data

@patch('oss.get_db_connection')
def test_long_input_fields(mock_conn, client):
    mock_conn.return_value.cursor.return_value = MagicMock()
    response = client.post('/add_customer', data={
        'CustomerID': '999', 'CustomerName': 'A'*300, 'PhoneNumber': '1'*50,
        'Email': 'a@a.com', 'Address': 'B'*500})
    assert response.status_code == 302

@patch('oss.get_db_connection')
def test_login_response_time(mock_conn, client):
    import time
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = (1,)
    mock_conn.return_value.cursor.return_value = mock_cursor

    start = time.time()
    client.post('/', data={'CustomerID': '1', 'CustomerName': 'John'})
    end = time.time()
    assert (end - start) < 1.0

@patch('oss.get_db_connection')
def test_product_list_response_time(mock_conn, client):
    import time
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [(1, 'Product')]
    mock_conn.return_value.cursor.return_value = mock_cursor

    with client.session_transaction() as sess:
        sess['customer_id'] = '1'
    start = time.time()
    response = client.get('/products')
    end = time.time()
    assert response.status_code == 200
    assert (end - start) < 1.5
