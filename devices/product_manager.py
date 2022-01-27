"""
Manage products in the shelf: insert and remove.
"""
import asyncio
import logging
import os
from pathlib import Path
from typing import List

import aiofile
import aiopubsub
import boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError
from marshmallow import Schema, fields, post_load
from marshmallow.exceptions import ValidationError
from models.product import Product, ProductSchema, ProductTag


class ProductShelf:
    #pylint: disable=too-few-public-methods
    """TODO"""
    def __init__(self, products: List[Product]):
        self.products = products

class ProductShelfSchema(Schema):
    """TODO"""
    products = fields.List(fields.Nested(ProductSchema))

    @post_load
    def make_user(self, data, **kwargs):
        #pylint: disable=missing-function-docstring,unused-argument,no-self-use
        return ProductShelf(**data)


class ProductManager:
    #pylint: disable=too-many-instance-attributes
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
        self.__subscribe_new_tag_key = aiopubsub.Key("*", "tag", "*")
        self.__subscribe_update_key = aiopubsub.Key("*", "update", "*")
        self.__publisher = aiopubsub.Publisher(self.__message_bus, prefix = aiopubsub.Key("productmanager"))
        self.__publish_key = aiopubsub.Key("productmanager", "product")

        self.__logger = logging.getLogger("product_manager")

    async def start(self) -> None:
        """TODO"""
        await self.__load_products_file()
        self.__subscriber.add_async_listener(self.__subscribe_new_tag_key, self.__on_new_tag)
        self.__subscriber.add_async_listener(self.__subscribe_update_key, self.__on_product_update)
        await self.__send_product_to_display()

    async def __on_new_tag(self, key, product: ProductTag):
        self.__logger.info("Get new product %s from %s", product, key)
        await self.__insert_remove_product_logic(product)
        self.__logger.debug("Product list: %s", self.__products.products)

    async def __on_product_update(self, key, product: Product):
        self.__logger.debug("Receive product update: %s", product)
        product_in_shelf = list(filter(lambda p: p.code == product.code and p.lot == product.lot, self.__products.products))
        if not product_in_shelf:
            self.__logger.debug("The product is not in the shelf, skip operation")
        else:
            self.__logger.debug("Product found in the shelf! Updating info")
            index = self.__products.products.index(product_in_shelf[0])
            self.__products.products.pop(index) # remove the old product info
            self.__products.products.insert(index, product) # update info
            await self.__write_products_file(ProductShelfSchema().dumps(self.__products))
            if index == 0:
                await self.__send_product_to_display()

    async def __insert_remove_product_logic(self, product: ProductTag) -> None:
        def callback():
            try:
                products_result = self.__table.scan(
                    FilterExpression=Attr("code").eq(product.code) & Attr("lot").eq(product.lot)
                )
                return products_result.get("Items", [])
            except ClientError as error:
                self.__logger.error(error)
                return []

        result = await self.__loop.run_in_executor(None, callback)

        if not result:
            self.__logger.warning("No product with code %s and lot %s was found", product.code, product.lot)
        else:
            # The product exist in the DB
            readed_product = ProductSchema().load(result[0])
            self.__logger.debug("Now products %s", self.__products.products)
            product_in_list = list(
                filter(
                    lambda p: p.code == readed_product.code and p.lot == readed_product.lot,
                    self.__products.products
                )
            )

            if not product_in_list:
                self.__logger.debug("The product not exist, insert in the shelf")
                self.__products.products.append(readed_product)
            else:
                self.__logger.debug("The product is in the shelf, remove it from shelf")
                index = self.__products.products.index(product_in_list[0])
                self.__products.products.pop(index)

            await self.__write_products_file(ProductShelfSchema().dumps(self.__products))
            await self.__send_product_to_display()

    async def __load_products_file(self) -> None:
        async with aiofile.async_open(self.__save_path, 'r') as file:
            content = await file.read()
            try:
                self.__products = ProductShelfSchema().loads(content)
                self.__logger.debug("Load from file: %s", self.__products)
            except ValidationError as error:
                self.__logger.error(error)
                self.__logger.debug("Failed to load products")
                self.__logger.debug("Fall back to %s", self.__products.products)

    async def __write_products_file(self, payload) -> None:
        async with aiofile.async_open(self.__save_path, 'w') as file:
            await file.write(payload)

    async def __send_product_to_display(self):
        if len(self.__products.products) > 0:
            product_display = self.__products.products[0]
        else:
            product_display = None

        self.__publisher.publish(self.__publish_key, product_display)
