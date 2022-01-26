"""
TODO.
"""
from marshmallow import Schema, fields

class Product:
    """TODO"""
    def __init__(self, product_id: str, name: str, price: float, expiration_date: str):
        self.product_id = product_id
        self.name = name
        self.price = price
        self.expiration_date = expiration_date

class ProductSchema(Schema):
    """
    Class representing a Product's tag.
    """
    product_id = fields.Str()
    name = fields.Str()
    price = fields.Float()
    expiration_date = fields.Str()
