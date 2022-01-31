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
from models.product import Product, ProductTag
from pydantic import BaseModel, ValidationError
from typing import List
import json
import uuid


class ProductShelf(BaseModel):
    #pylint: disable=too-few-public-methods
    """TODO"""
    products: List[Product] = []


class ProductManager:
    #pylint: disable=too-many-instance-attributes
    """
    TODO.
    """
    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        message_bus: aiopubsub.Hub,
        shelf_id: int,
        startup_event: asyncio.Event
    ):
        self.__loop = loop
        self.__startup_event = startup_event
        self.__message_bus = message_bus
        self.__shelf_id = shelf_id
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
        self.__product_shelf_table = self.__db.Table("ProductShelf-n5ua2pmmmrcibp6oynfn73yccq-sc")

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
        await self.__startup_event.wait()
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
            await self.__write_products_file(self.__products.json())
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
            readed_product = Product(**result[0], tag_id=product.id)
            self.__logger.debug("Now products %s, key: %s", self.__products.products, product.id)
            product_in_list = list(filter(lambda p: p.tag_id == product.id, self.__products.products))
            self.__logger.debug("After filter %s", product_in_list)

            if not product_in_list:
                self.__logger.debug("The product not exist, insert in the shelf")
                self.__products.products.append(readed_product)
                await self.__insert_product_in_shelf_db(readed_product)
            else:
                self.__logger.debug("The product is in the shelf, remove it from shelf")
                index = self.__products.products.index(product_in_list[0])
                self.__products.products.pop(index)
                await self.__remove_product_in_shelf_db(product_in_list[0])

            await self.__write_products_file(self.__products.json())
            await self.__send_product_to_display()

    async def __insert_product_in_shelf_db(self, product: Product):
        def query_shelf():
            try:
                product_in_shelf = self.__product_shelf_table.scan(
                    FilterExpression=Attr("shelfId").eq(self.__shelf_id) & Attr("productShelfProductId").eq(product.id)
                )
                return product_in_shelf.get("Items", [])
            except ClientError as error:
                self.__logger.error(error)
                return []
        def update_quantity(id: str, quantity: int):
            try:
                response = self.__product_shelf_table.update_item(
                    Key={
                        'id': id
                    },
                    UpdateExpression="set quantity=:q",
                    ExpressionAttributeValues={
                        ':q': quantity
                    }
                )
                return response
            except ClientError as error:
                self.__logger.error(error)
                return []
        
        result = await self.__loop.run_in_executor(None, query_shelf)
        if not result:
            self.__logger.debug("No product is in this shelf, create new record")
            response = self.__product_shelf_table.put_item(
                Item={
                    'id': str(uuid.uuid4()),
                    'shelfId': self.__shelf_id,
                    'productShelfProductId': product.id,
                    'quantity': 1
                }
            )
            self.__logger.debug("Insert product shelf result: %s", response)
        else:
            self.__logger.debug("Other products are in the shelf, increare quantity")
            quantity = result[0].get("quantity")
            response = await self.__loop.run_in_executor(None, update_quantity, result[0].get("id"), quantity+1)
            self.__logger.debug("Update quantity result: %s", response)

    async def __remove_product_in_shelf_db(self, product: Product):
        def query_shelf():
            try:
                product_in_shelf = self.__product_shelf_table.scan(
                    FilterExpression=Attr("shelfId").eq(self.__shelf_id) & Attr("productShelfProductId").eq(product.id)
                )
                return product_in_shelf.get("Items", [])
            except ClientError as error:
                self.__logger.error(error)
                return []

        def update_quantity(id: str, quantity: int):
            try:
                response = self.__product_shelf_table.update_item(
                    Key={
                        'id': id
                    },
                    UpdateExpression="set quantity=:q",
                    ExpressionAttributeValues={
                        ':q': quantity
                    }
                )
                return response
            except ClientError as error:
                self.__logger.error(error)
                return []
        
        def delete_item(id: str):
            try:
                response = self.__product_shelf_table.delete_item(
                    Key={'id': id},
                )
                return response
            except ClientError as error:
                self.__logger.error(error)
                return []

        result = await self.__loop.run_in_executor(None, query_shelf)
        if not result:
            self.__logger.debug("No product is in this shelf, create new record")
        else:
            self.__logger.debug("Other products are in the shelf, decrease quantity")
            quantity = result[0].get("quantity")
            if quantity == 1: # since we have only 1 item to remove, delete the record in DB
                self.__logger.debug("The product quantity of the product is 0, delete record")
                await self.__loop.run_in_executor(None, delete_item, result[0].get("id"))
            else:
                response = await self.__loop.run_in_executor(None, update_quantity, result[0].get("id"), quantity-1)
                self.__logger.debug("Update quantity result: %s", response)

    async def __load_products_file(self):
        content = None
        async with aiofile.async_open(self.__save_path, 'r') as file:
            content = await file.read()
        try:
            obj = json.loads(content)
            self.__products = ProductShelf(**obj)
            self.__logger.debug("Load from file: %s", self.__products)
        except (json.JSONDecodeError, ValidationError) as error:
            self.__logger.error(error)
            self.__logger.debug("Failed to load products")
            self.__logger.debug("Fall back to %s", self.__products.products)

    async def __write_products_file(self, payload) -> None:
        async with aiofile.async_open(self.__save_path, 'w') as file:
            await file.write(payload)

    async def __send_product_to_display(self):
        if len(self.__products.products) > 0:
            product_display = self.__products.products[-1]
        else:
            product_display = None

        self.__publisher.publish(self.__publish_key, product_display)
