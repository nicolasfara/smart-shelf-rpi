"""
TODO.
"""
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Product:
    """
    Class representing a Product's tag.
    """
    product_id: str
    name: str
    price: float
    expiration_day: datetime

def create_product(product_id: str, name: str, price: str, expiration_day: str) -> Product:
    """
    Create a new Product object from parameters.
    """
    exp_date = datetime.strptime(expiration_day, "%d/%m/%Y")
    return Product(product_id=product_id, name=name, price=price, expiration_day=exp_date)
