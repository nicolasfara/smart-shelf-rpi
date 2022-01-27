"""
TODO.
"""
from marshmallow import Schema, fields, post_load, EXCLUDE

class Product:
    """TODO"""
    def __init__(self, code: str, lot: int, name: str, price: float, expirationDate: str, inPromo: bool, promoPrice: float):
        self.code = code
        self.lot = lot
        self.name = name
        self.price = price
        self.expirationDate = expirationDate
        self.inPromo = inPromo
        self.promoPrice = promoPrice

class ProductSchema(Schema):
    """
    Class representing a Product's tag.
    """
    class Meta:
        unknown = EXCLUDE

    code = fields.Str()
    lot = fields.Int()
    name = fields.Str()
    price = fields.Float()
    expirationDate = fields.Str()
    inPromo = fields.Boolean(required=False, missing=False)
    promoPrice = fields.Float(required=False, missing=None)

    @post_load
    def make_user(self, data, **kwargs):
        return Product(**data)
