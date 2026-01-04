from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.config import get_settings
from app.database import engine, Base
from app.api import products, orders, health

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    logger.info("Starting up application...")
    
    # Create database tables
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")


# Create FastAPI application
app = FastAPI(
    title="Distributed E-Commerce Order System",
    description="""
    A scalable backend API for handling product sales with:
    
    - **Product Management**: Full CRUD operations for products
    - **Order Processing**: Purchase endpoint with race condition handling
    - **Background Tasks**: Celery workers for async order processing
    - **Caching**: Redis-based caching for product details
    
    ## Features
    
    ### Stock Management & Race Condition Handling
    The system uses PostgreSQL's `SELECT FOR UPDATE` to handle concurrent purchases.
    When multiple users try to buy the last item simultaneously, only one succeeds.
    
    ### Background Processing
    Orders are processed asynchronously using Celery workers.
    After an order is created, a background task simulates external API calls.
    
    ### Caching
    Product details are cached in Redis with a 5-minute TTL for improved performance.
    """,
    version="1.0.0",
    contact={
        "name": "API Support",
        "email": "support@example.com"
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT"
    },
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(health.router, prefix="/api/v1")
app.include_router(products.router, prefix="/api/v1")
app.include_router(orders.router, prefix="/api/v1")


@app.get("/", tags=["Root"])
def root():
    """Root endpoint with API information."""
    return {
        "name": "Distributed E-Commerce Order System",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/api/v1/health"
    }
