"""
TODO.
"""
import asyncio
import logging
from typing import Tuple

import adafruit_ssd1306
import aiopubsub
import board
from PIL import Image, ImageDraw, ImageFont

from models.product import Product

font_12 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
font_18 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)

class Display:
    """
    TODO.
    """
    def __init__(self, loop: asyncio.AbstractEventLoop, message_bus: aiopubsub.Hub) -> None:
        self.__oled = adafruit_ssd1306.SSD1306_I2C(128, 64, board.I2C(), addr=0x3c)

        self.__image = Image.new("1", (self.__oled.width, self.__oled.height))
        self.__draw = ImageDraw.Draw(self.__image)

        self.__oled.fill(0)
        self.__oled.show()

        self.__loop = loop
        self.__message_bus = message_bus
        self.__subscriber = aiopubsub.Subscriber(self.__message_bus, "display")
        self.__subscribe_key = aiopubsub.Key("*", "tag", "*")

        logging.debug("Display instance created")

    async def start_display(self) -> None:
        """
        TODO.
        """
        await self.__splash_screen()
        await asyncio.sleep(2)

        await self.__clean_screen()

        logging.info("Display setup complete")

        self.__subscriber.add_async_listener(self.__subscribe_key, self.__on_new_tag)

    # Private methods

    async def __setup_productview_frame(self) -> None:
        def setup_ui_frame():
            self.__draw.rectangle((0, 16, self.__oled.width-1, self.__oled.height-1), outline=True, fill=False)
            self.__draw.line((0, 16, 127, 16), fill=True)
            self.__oled.image(self.__image)

        await self.__loop.run_in_executor(None, setup_ui_frame)

    async def __on_new_tag(self, key, product: Product) -> None:
        logging.debug("New message with key: %s", key)
        await self.__configure_product_view(product)

    async def __splash_screen(self) -> None:
        await self.__setup_productview_frame()
        await self.__write_text((12, 20), "Smart shelf", font=font_18)
        await self.__write_text((32, 45), "Loading...")
        await self.__show_screen()

    async def __configure_product_view(self, product: Product) -> None:
        price = format(product.price, ".2f")
        await self.__clean_screen()
        await self.__setup_productview_frame()
        await self.__write_text((2, 1), product.name)
        await self.__write_text((5, 16), f"{price} \u20ac", font=font_18)
        await self.__write_text((5, 34), f"Art.: {product.code}")
        await self.__write_text((5, 47), f"Scad.: {product.expirationDate}")
        await self.__show_screen()

    async def __show_screen(self):
        def show():
            self.__oled.show()
        await self.__loop.run_in_executor(None, show)

    async def __write_text(self, pos: Tuple[int, int], text: str, font = font_12) -> None:
        def callback():
            self.__draw.text(pos, text, font=font, fill=255)
            self.__oled.image(self.__image)

        await self.__loop.run_in_executor(None, callback)

    async def __clean_screen(self) -> None:
        def callback():
            self.__draw.rectangle((0, 0, self.__oled.width, self.__oled.height), 0, 0)
            self.__oled.image(self.__image)
            self.__oled.show()

        await self.__loop.run_in_executor(None, callback)
