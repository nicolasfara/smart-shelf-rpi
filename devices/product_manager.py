"""
Manage products in the shelf: insert and remove.
"""
import asyncio
import boto3
import os
import logging
from pathlib import Path
from typing import List

import aiofile
import aiopubsub
from marshmallow import Schema, fields
from marshmallow.exceptions import ValidationError
from models.product import Product, ProductSchema


class ProductShelf:
    """TODO"""
    def __init__(self, products: List[Product]):
        self.products = products

class ProductShelfSchema(Schema):
    """TODO"""
    products = fields.List(fields.Nested(ProductSchema))


class ProductManager:
    """
    TODO.
    """
    def __init__(self, loop: asyncio.AbstractEventLoop, message_bus: aiopubsub.Hub):
        self.__loop = loop
        self.__message_bus = message_bus

        self.__save_path = Path.home() / ".products.json"
        self.__save_path.touch(exist_ok=True)
        self.__products = ProductShelf(products=[])

        self.__db = boto3.resource(
            "dynamodb",
            region_name="eu-west-1",
            aws_access_key_id=os.environ["AWS_BACKEND_KEY"],
            aws_secret_access_key=os.environ["AWS_BACKEND_SECRET"]
        )
        self.__table = self.__db.Table("Product-n5ua2pmmmrcibp6oynfn73yccq-sc")

        self.__subscriber = aiopubsub.Subscriber(self.__message_bus, "ProductManager")
        self.__subscribe_key = aiopubsub.Key("*", "tag", "*")

        self.__logger = logging.getLogger("product_manager")

    async def start(self) -> None:
        """TODO"""
        await self.__load_products_file()
        self.__subscriber.add_async_listener(self.__subscribe_key, self.__on_new_tag)

    async def __on_new_tag(self, key, product: Product):
        self.__logger.info("Get new product %s from %s", product, key)
        await self.__insert_remove_logic(product)
        self.__logger.debug("Product list: %s", self.__products.products)

    async def __insert_remove_logic(self, product: Product) -> None:
        pass

    async def __load_products_file(self) -> None:
        async with aiofile.async_open(self.__save_path, 'r') as file:
            content = await file.read()
            try:
                self.__products = ProductShelfSchema().load(content)
            except ValidationError:
                self.__logger.debug("Failed to load products")
                self.__logger.debug("Fall back to %s", self.__products.products)
