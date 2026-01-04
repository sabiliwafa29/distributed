"""Tests for Order API endpoints."""
from unittest.mock import patch


def test_create_order_success(client):
    """Test creating an order successfully."""
    # First create a product
    product_response = client.post(
        "/api/v1/products/",
        json={"name": "Test Product", "price": 100.00, "stock": 10}
    )
    product_id = product_response.json()["id"]
    
    # Create order (mock Celery task to avoid actual task execution)
    with patch("app.api.orders.process_order.delay"):
        response = client.post(
            "/api/v1/orders/",
            json={"product_id": product_id, "quantity": 2}
        )
    
    assert response.status_code == 201
    data = response.json()
    assert data["product_id"] == product_id
    assert data["quantity"] == 2
    assert data["total_price"] == 200.00
    assert data["status"] == "pending"


def test_create_order_insufficient_stock(client):
    """Test order fails when insufficient stock."""
    # Create product with limited stock
    product_response = client.post(
        "/api/v1/products/",
        json={"name": "Limited Product", "price": 50.00, "stock": 3}
    )
    product_id = product_response.json()["id"]
    
    # Try to order more than available
    with patch("app.api.orders.process_order.delay"):
        response = client.post(
            "/api/v1/orders/",
            json={"product_id": product_id, "quantity": 5}
        )
    
    assert response.status_code == 400
    assert "Insufficient stock" in response.json()["detail"]


def test_create_order_product_not_found(client):
    """Test order fails when product doesn't exist."""
    with patch("app.api.orders.process_order.delay"):
        response = client.post(
            "/api/v1/orders/",
            json={"product_id": 9999, "quantity": 1}
        )
    
    assert response.status_code == 404


def test_order_decrements_stock(client):
    """Test that creating an order decrements product stock."""
    # Create product
    product_response = client.post(
        "/api/v1/products/",
        json={"name": "Stock Test", "price": 25.00, "stock": 10}
    )
    product_id = product_response.json()["id"]
    
    # Create order
    with patch("app.api.orders.process_order.delay"):
        client.post(
            "/api/v1/orders/",
            json={"product_id": product_id, "quantity": 3}
        )
    
    # Check stock was decremented
    product = client.get(f"/api/v1/products/{product_id}").json()
    assert product["stock"] == 7  # 10 - 3


def test_multiple_orders_deplete_stock(client):
    """Test multiple orders correctly deplete stock."""
    # Create product with limited stock
    product_response = client.post(
        "/api/v1/products/",
        json={"name": "Depleting Product", "price": 10.00, "stock": 5}
    )
    product_id = product_response.json()["id"]
    
    # Create first order
    with patch("app.api.orders.process_order.delay"):
        response1 = client.post(
            "/api/v1/orders/",
            json={"product_id": product_id, "quantity": 3}
        )
    assert response1.status_code == 201
    
    # Create second order (should succeed)
    with patch("app.api.orders.process_order.delay"):
        response2 = client.post(
            "/api/v1/orders/",
            json={"product_id": product_id, "quantity": 2}
        )
    assert response2.status_code == 201
    
    # Third order should fail (no stock)
    with patch("app.api.orders.process_order.delay"):
        response3 = client.post(
            "/api/v1/orders/",
            json={"product_id": product_id, "quantity": 1}
        )
    assert response3.status_code == 400


def test_get_order(client):
    """Test getting an order by ID."""
    # Create product and order
    product_response = client.post(
        "/api/v1/products/",
        json={"name": "Test", "price": 50.00, "stock": 10}
    )
    product_id = product_response.json()["id"]
    
    with patch("app.api.orders.process_order.delay"):
        order_response = client.post(
            "/api/v1/orders/",
            json={"product_id": product_id, "quantity": 1}
        )
    order_id = order_response.json()["id"]
    
    # Get order
    response = client.get(f"/api/v1/orders/{order_id}")
    
    assert response.status_code == 200
    assert response.json()["id"] == order_id


def test_list_orders(client):
    """Test listing orders with pagination."""
    # Create product
    product_response = client.post(
        "/api/v1/products/",
        json={"name": "Multi Order", "price": 10.00, "stock": 100}
    )
    product_id = product_response.json()["id"]
    
    # Create multiple orders
    with patch("app.api.orders.process_order.delay"):
        for _ in range(15):
            client.post(
                "/api/v1/orders/",
                json={"product_id": product_id, "quantity": 1}
            )
    
    # List orders with pagination
    response = client.get("/api/v1/orders/?page=1&page_size=10")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 10
    assert data["total"] == 15


def test_get_order_status(client):
    """Test getting order status."""
    # Create product and order
    product_response = client.post(
        "/api/v1/products/",
        json={"name": "Status Test", "price": 30.00, "stock": 5}
    )
    product_id = product_response.json()["id"]
    
    with patch("app.api.orders.process_order.delay"):
        order_response = client.post(
            "/api/v1/orders/",
            json={"product_id": product_id, "quantity": 1}
        )
    order_id = order_response.json()["id"]
    
    # Get status
    response = client.get(f"/api/v1/orders/{order_id}/status")
    
    assert response.status_code == 200
    data = response.json()
    assert data["order_id"] == order_id
    assert data["status"] == "pending"
