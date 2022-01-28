"""
TODO.
"""
from marshmallow import Schema, fields, post_load, EXCLUDE

class Product:
    #pylint: disable=too-few-public-methods
    """Model of a product with it's info"""
    def __init__(
        #pylint: disable=too-many-arguments
        self,
        code: str,
        lot: int,
        name: str,
        price: float,
        expirationDate: str, #pylint: disable=invalid-name
        inPromo: bool, #pylint: disable=invalid-name
        promoPrice: float #pylint: disable=invalid-name
    ):
        self.code = code
        self.lot = lot
        self.name = name
        self.price = price
        self.expirationDate = expirationDate #pylint: disable=invalid-name
        self.inPromo = inPromo #pylint: disable=invalid-name
        self.promoPrice = promoPrice #pylint: disable=invalid-name

class ProductSchema(Schema):
    #pylint: disable=missing-class-docstring
    class Meta:
        #pylint: disable=missing-class-docstring,too-few-public-methods
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
        #pylint: disable=missing-function-docstring,unused-argument,no-self-use
        return Product(**data)

class ProductTag:
    #pylint: disable=too-few-public-methods
    """Model the tag info of a product"""

    def __init__(self, code: str, lot: int):
        self.code = code
        self.lot = lot

class ProductTagSchema(Schema):
    #pylint: disable=missing-class-docstring
    code = fields.Str()
    lot = fields.Int()

    @post_load
    def make_user(self, data, **kwargs):
        #pylint: disable=missing-function-docstring,unused-argument,no-self-use
        return ProductTag(**data)
