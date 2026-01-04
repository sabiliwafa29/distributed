# Distributed E-Commerce Order System

A scalable backend API for handling product sales with data consistency, background task processing, and caching.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue)
![Redis](https://img.shields.io/badge/Redis-7-red)
![Celery](https://img.shields.io/badge/Celery-5.3-green)
![Docker](https://img.shields.io/badge/Docker-Compose-blue)

## 📋 Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Race Condition Handling](#race-condition-handling)
- [Quick Start](#quick-start)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Configuration](#configuration)

## ✨ Features

- **Product API**: Full CRUD operations for products (ID, Name, Price, Stock)
- **Order API**: Purchase endpoint with stock validation
- **Race Condition Handling**: Pessimistic locking to prevent overselling
- **Background Tasks**: Celery workers for async order processing
- **Caching**: Redis-based caching for product details
- **Monitoring**: Flower dashboard for Celery task monitoring
- **Health Checks**: Database and Redis connectivity checks

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Client/API    │────▶│   FastAPI Web   │────▶│   PostgreSQL    │
│    Consumer     │     │     Server      │     │    Database     │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                                 │ Publish Task
                                 ▼
                        ┌─────────────────┐
                        │      Redis      │
                        │  (Broker/Cache) │
                        └────────┬────────┘
                                 │
                                 │ Consume Task
                                 ▼
                        ┌─────────────────┐
                        │  Celery Worker  │
                        │ (Background Job)│
                        └─────────────────┘
```

### Components

| Service | Port | Description |
|---------|------|-------------|
| Web API | 8000 | FastAPI application |
| PostgreSQL | 5432 | Primary database |
| Redis | 6379 | Cache & message broker |
| Celery Worker | - | Background task processor |
| Flower | 5555 | Celery monitoring dashboard |

## 🔒 Race Condition Handling

### The Problem

When multiple users try to purchase the last item of a product simultaneously, we need to ensure:
- Only one user successfully completes the purchase
- Stock never goes negative
- No overselling occurs

### Our Solution: Pessimistic Locking

We use PostgreSQL's `SELECT FOR UPDATE` to implement pessimistic locking:

```python
# From app/services/order_service.py

product = (
    self.db.query(Product)
    .filter(Product.id == product_id)
    .with_for_update()  # Acquires row-level lock
    .first()
)

if product.stock < quantity:
    raise InsufficientStockError(...)

# Safely deduct stock
product.stock -= quantity
```

### How It Works

1. **Transaction Starts**: When a purchase request arrives, a database transaction begins
2. **Lock Acquired**: `SELECT FOR UPDATE` locks the product row
3. **Stock Check**: We verify sufficient stock is available
4. **Stock Deduction**: Stock is decremented atomically
5. **Lock Released**: Transaction commits, releasing the lock

### Concurrent Request Scenario

```
Time    User A                          User B
─────────────────────────────────────────────────────────
T1      SELECT ... FOR UPDATE           
        (Acquires lock on Product #1)
        
T2      Stock = 1, Quantity = 1         SELECT ... FOR UPDATE
        Check passes ✓                   (Waits for lock...)
        
T3      UPDATE stock = 0                 (Still waiting...)
        COMMIT
        (Lock released)
        
T4      ✅ Order Created                  (Lock acquired)
                                         Stock = 0, Quantity = 1
                                         Check fails ✗
                                         
T5                                       ❌ InsufficientStockError
```

### Alternative: Optimistic Locking

We also provide an optimistic locking approach using atomic UPDATE:

```sql
UPDATE products 
SET stock = stock - :quantity
WHERE id = :product_id 
AND stock >= :quantity
```

This approach is better for low-contention scenarios but may require retries.

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Git

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/distributed-ecommerce.git
   cd distributed-ecommerce
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   ```

3. **Start all services**
   ```bash
   docker-compose up -d --build
   ```

4. **Verify services are running**
   ```bash
   docker-compose ps
   ```

5. **Check health status**
   ```bash
   curl http://localhost:8000/api/v1/health/ready
   ```

### Access Points

| Service | URL |
|---------|-----|
| API Documentation (Swagger) | http://localhost:8000/docs |
| API Documentation (ReDoc) | http://localhost:8000/redoc |
| Flower (Celery Monitor) | http://localhost:5555 |

### Stop Services

```bash
docker-compose down
```

To remove all data (volumes):
```bash
docker-compose down -v
```

## 📚 API Documentation

### Base URL

```
http://localhost:8000/api/v1
```

### Endpoints Overview

#### Products

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/products` | List all products (paginated) |
| POST | `/products` | Create a new product |
| GET | `/products/{id}` | Get product by ID |
| GET | `/products/{id}/cached` | Get product from cache |
| PUT | `/products/{id}` | Update a product |
| DELETE | `/products/{id}` | Delete a product |

#### Orders

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/orders` | List all orders (paginated) |
| POST | `/orders` | Create an order (purchase) |
| GET | `/orders/{id}` | Get order by ID |
| GET | `/orders/{id}/status` | Get order processing status |

#### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Basic health check |
| GET | `/health/ready` | Readiness check (DB + Redis) |
| GET | `/health/cache/stats` | Cache statistics |

### Example Requests

#### Create Product
```bash
curl -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{
    "name": "iPhone 15 Pro",
    "price": 999.99,
    "stock": 100
  }'
```

#### Get Product (with caching)
```bash
curl http://localhost:8000/api/v1/products/1/cached
```

#### Create Order (Purchase)
```bash
curl -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 1,
    "quantity": 2
  }'
```

#### List Orders
```bash
curl "http://localhost:8000/api/v1/orders?page=1&page_size=10"
```

### Response Examples

#### Successful Order Creation
```json
{
  "id": 1,
  "product_id": 1,
  "quantity": 2,
  "total_price": 1999.98,
  "status": "pending",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

#### Insufficient Stock Error
```json
{
  "detail": "Insufficient stock. Available: 0, Requested: 1"
}
```

## 🧪 Testing

### Run Tests

```bash
# Run all tests
docker-compose exec web pytest

# Run with coverage
docker-compose exec web pytest --cov=app --cov-report=html

# Run specific test file
docker-compose exec web pytest tests/test_orders.py -v
```

### Test Race Condition

You can test the race condition handling with concurrent requests:

```bash
# Create a product with stock = 1
curl -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{"name": "Limited Item", "price": 99.99, "stock": 1}'

# Send multiple concurrent purchase requests
for i in {1..5}; do
  curl -X POST http://localhost:8000/api/v1/orders \
    -H "Content-Type: application/json" \
    -d '{"product_id": 1, "quantity": 1}' &
done
wait

# Only one should succeed, others should get "Insufficient stock" error
```

## 📁 Project Structure

```
distributed/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Configuration settings
│   ├── database.py          # Database connection setup
│   ├── models/              # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── product.py       # Product model
│   │   └── order.py         # Order model
│   ├── schemas/             # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── product.py       # Product request/response schemas
│   │   └── order.py         # Order request/response schemas
│   ├── api/                 # API route handlers
│   │   ├── __init__.py
│   │   ├── products.py      # Product CRUD endpoints
│   │   ├── orders.py        # Order endpoints
│   │   └── health.py        # Health check endpoints
│   ├── services/            # Business logic layer
│   │   ├── __init__.py
│   │   ├── product_service.py
│   │   └── order_service.py # Contains race condition handling
│   ├── tasks/               # Celery background tasks
│   │   ├── __init__.py
│   │   ├── celery_app.py    # Celery configuration
│   │   └── order_tasks.py   # Order processing tasks
│   └── utils/               # Utility modules
│       ├── __init__.py
│       └── cache.py         # Redis caching utilities
├── tests/                   # Test files
├── docker-compose.yml       # Docker services configuration
├── Dockerfile               # Application container definition
├── requirements.txt         # Python dependencies
├── .env.example             # Environment variables template
├── .gitignore
└── README.md
```

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://postgres:postgres@db:5432/ecommerce` | PostgreSQL connection string |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection for caching |
| `CELERY_BROKER_URL` | `redis://redis:6379/1` | Celery message broker |
| `CELERY_RESULT_BACKEND` | `redis://redis:6379/2` | Celery result backend |
| `DEBUG` | `True` | Debug mode |
| `CACHE_TTL` | `300` | Cache TTL in seconds (5 minutes) |

### Scaling Workers

To scale Celery workers:

```bash
docker-compose up -d --scale celery_worker=4
```

## 📝 Development

### Local Development (without Docker)

1. Create virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   .\venv\Scripts\activate   # Windows
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Start PostgreSQL and Redis locally

4. Run the application:
   ```bash
   uvicorn app.main:app --reload
   ```

5. Start Celery worker:
   ```bash
   celery -A app.tasks.celery_app worker --loglevel=info
   ```

### Viewing Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f web
docker-compose logs -f celery_worker
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

Made with ❤️ using FastAPI, PostgreSQL, Redis, and Celery
