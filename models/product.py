"""
TODO.
"""
from typing import Optional

from pydantic import BaseModel


class Product(BaseModel):
    #pylint: disable=too-few-public-methods
    """Model of a product with it's info"""
    id: str
    tag_id: Optional[str]
    code: str
    lot: int
    name: str
    price: float
    expirationDate: str #pylint: disable=invalid-name
    inPromo: bool #pylint: disable=invalid-name
    promoPrice: Optional[float] = None #pylint: disable=invalid-name

class ProductTag(BaseModel):
    #pylint: disable=too-few-public-methods
    """Model the tag info of a product"""
    id: str
    code: str
    lot: int
