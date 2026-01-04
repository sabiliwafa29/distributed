"""Tests for Product API endpoints."""


def test_create_product(client):
    """Test creating a new product."""
    response = client.post(
        "/api/v1/products/",
        json={
            "name": "Test Product",
            "price": 99.99,
            "stock": 10
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Product"
    assert data["price"] == 99.99
    assert data["stock"] == 10
    assert "id" in data
    assert "created_at" in data


def test_create_product_invalid_price(client):
    """Test creating product with invalid price fails."""
    response = client.post(
        "/api/v1/products/",
        json={
            "name": "Test Product",
            "price": -10.00,  # Invalid: negative price
            "stock": 10
        }
    )
    
    assert response.status_code == 422  # Validation error


def test_create_product_invalid_stock(client):
    """Test creating product with negative stock fails."""
    response = client.post(
        "/api/v1/products/",
        json={
            "name": "Test Product",
            "price": 99.99,
            "stock": -5  # Invalid: negative stock
        }
    )
    
    assert response.status_code == 422


def test_get_product(client):
    """Test getting a product by ID."""
    # First create a product
    create_response = client.post(
        "/api/v1/products/",
        json={"name": "Test Product", "price": 50.00, "stock": 5}
    )
    product_id = create_response.json()["id"]
    
    # Get the product
    response = client.get(f"/api/v1/products/{product_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == product_id
    assert data["name"] == "Test Product"


def test_get_product_not_found(client):
    """Test getting non-existent product returns 404."""
    response = client.get("/api/v1/products/9999")
    
    assert response.status_code == 404


def test_list_products(client):
    """Test listing products with pagination."""
    # Create multiple products
    for i in range(15):
        client.post(
            "/api/v1/products/",
            json={"name": f"Product {i}", "price": 10.00 + i, "stock": 10}
        )
    
    # Get first page
    response = client.get("/api/v1/products/?page=1&page_size=10")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 10
    assert data["total"] == 15
    assert data["total_pages"] == 2


def test_update_product(client):
    """Test updating a product."""
    # Create product
    create_response = client.post(
        "/api/v1/products/",
        json={"name": "Original Name", "price": 50.00, "stock": 10}
    )
    product_id = create_response.json()["id"]
    
    # Update product
    response = client.put(
        f"/api/v1/products/{product_id}",
        json={"name": "Updated Name", "price": 75.00}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["price"] == 75.00
    assert data["stock"] == 10  # Stock should remain unchanged


def test_delete_product(client):
    """Test deleting a product."""
    # Create product
    create_response = client.post(
        "/api/v1/products/",
        json={"name": "To Delete", "price": 25.00, "stock": 5}
    )
    product_id = create_response.json()["id"]
    
    # Delete product
    response = client.delete(f"/api/v1/products/{product_id}")
    assert response.status_code == 204
    
    # Verify it's deleted
    get_response = client.get(f"/api/v1/products/{product_id}")
    assert get_response.status_code == 404


def test_search_products(client):
    """Test searching products by name."""
    # Create products
    client.post(
        "/api/v1/products/",
        json={"name": "Apple iPhone", "price": 999.00, "stock": 10}
    )
    client.post(
        "/api/v1/products/",
        json={"name": "Samsung Galaxy", "price": 899.00, "stock": 15}
    )
    client.post(
        "/api/v1/products/",
        json={"name": "Apple MacBook", "price": 1999.00, "stock": 5}
    )
    
    # Search for Apple products
    response = client.get("/api/v1/products/?search=Apple")
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert all("Apple" in item["name"] for item in data["items"])
