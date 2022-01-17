from dataclasses import dataclass
from datetime import datetime

@dataclass
class Product:
    """
    Class representing a Product's tag.
    """
    id: str
    name: str
    price: float
    expiration_day: datetime

def create_product(id: str, name: str, price: str, expiration_day: str) -> Product:
    exp_date = datetime.strptime(expiration_day, "%d/%m/%Y")
    return Product(id=id, name=name, price=price, expiration_day=exp_date)