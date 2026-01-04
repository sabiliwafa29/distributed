from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Optional, List
import math

from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse
from app.utils.cache import cache_service


class ProductService:
    """
    Service class for Product CRUD operations.
    
    This service handles:
    - Creating new products
    - Reading products (with caching)
    - Updating products
    - Deleting products
    - Cache invalidation
    """
    
    CACHE_PREFIX = "product"
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, product_data: ProductCreate) -> Product:
        """
        Create a new product.
        
        Args:
            product_data: Product creation data
            
        Returns:
            Created product instance
        """
        product = Product(
            name=product_data.name,
            price=product_data.price,
            stock=product_data.stock
        )
        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)
        return product
    
    def get_by_id(self, product_id: int) -> Optional[Product]:
        """
        Get a product by ID with caching.
        
        First checks Redis cache, then falls back to database.
        Caches the result for future requests.
        
        Args:
            product_id: Product ID to look up
            
        Returns:
            Product instance or None if not found
        """
        # Try cache first
        cached = cache_service.get(self.CACHE_PREFIX, str(product_id))
        if cached:
            # Reconstruct from cache - but we need to get from DB for session
            pass  # For relationship support, we fetch from DB
        
        # Get from database
        product = self.db.query(Product).filter(Product.id == product_id).first()
        
        # Cache the result if found
        if product:
            self._cache_product(product)
        
        return product
    
    def get_by_id_cached(self, product_id: int) -> Optional[dict]:
        """
        Get product details from cache or database.
        Returns a dictionary (suitable for API response).
        
        Args:
            product_id: Product ID to look up
            
        Returns:
            Product data as dictionary or None
        """
        # Try cache first
        cached = cache_service.get(self.CACHE_PREFIX, str(product_id))
        if cached:
            return cached
        
        # Get from database
        product = self.db.query(Product).filter(Product.id == product_id).first()
        
        if product:
            product_dict = {
                "id": product.id,
                "name": product.name,
                "price": product.price,
                "stock": product.stock,
                "created_at": str(product.created_at),
                "updated_at": str(product.updated_at),
            }
            cache_service.set(self.CACHE_PREFIX, str(product_id), product_dict)
            return product_dict
        
        return None
    
    def get_all(
        self, 
        page: int = 1, 
        page_size: int = 10,
        search: str = None
    ) -> tuple[List[Product], int, int]:
        """
        Get paginated list of products.
        
        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page
            search: Optional search term for product name
            
        Returns:
            Tuple of (products list, total count, total pages)
        """
        query = self.db.query(Product)
        
        # Apply search filter if provided
        if search:
            query = query.filter(Product.name.ilike(f"%{search}%"))
        
        # Get total count
        total = query.count()
        total_pages = math.ceil(total / page_size) if total > 0 else 1
        
        # Apply pagination
        offset = (page - 1) * page_size
        products = query.order_by(Product.id.desc()).offset(offset).limit(page_size).all()
        
        return products, total, total_pages
    
    def update(self, product_id: int, product_data: ProductUpdate) -> Optional[Product]:
        """
        Update an existing product.
        
        Args:
            product_id: ID of product to update
            product_data: Update data (only non-None fields are updated)
            
        Returns:
            Updated product or None if not found
        """
        product = self.db.query(Product).filter(Product.id == product_id).first()
        
        if not product:
            return None
        
        # Update only provided fields
        update_data = product_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                setattr(product, field, value)
        
        self.db.commit()
        self.db.refresh(product)
        
        # Invalidate cache
        self._invalidate_cache(product_id)
        
        return product
    
    def delete(self, product_id: int) -> bool:
        """
        Delete a product.
        
        Args:
            product_id: ID of product to delete
            
        Returns:
            True if deleted, False if not found
        """
        product = self.db.query(Product).filter(Product.id == product_id).first()
        
        if not product:
            return False
        
        self.db.delete(product)
        self.db.commit()
        
        # Invalidate cache
        self._invalidate_cache(product_id)
        
        return True
    
    def _cache_product(self, product: Product) -> None:
        """Cache a product instance."""
        product_dict = {
            "id": product.id,
            "name": product.name,
            "price": product.price,
            "stock": product.stock,
            "created_at": str(product.created_at),
            "updated_at": str(product.updated_at),
        }
        cache_service.set(self.CACHE_PREFIX, str(product.id), product_dict)
    
    def _invalidate_cache(self, product_id: int) -> None:
        """Invalidate cache for a product."""
        cache_service.delete(self.CACHE_PREFIX, str(product_id))
