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

    def __init__(self, loop: asyncio.AbstractEventLoop, message_bus: aiopubsub.Hub) -> None:
        self.width = 128
        self.height = 64

        self._oled = adafruit_ssd1306.SSD1306_I2C(self.width, self.height, board.I2C(), addr=0x3c)

        self._image = Image.new("1", (self._oled.width, self._oled.height))
        self._draw = ImageDraw.Draw(self._image)

        self._oled.fill(0)
        self._oled.show()

        self._loop = loop
        self._message_bus = message_bus
        self._subscriber = aiopubsub.Subscriber(self._message_bus, "display")
        self._subscribe_key = aiopubsub.Key("*", "tag", "*")

        logging.debug("Display instance created")

    async def start_display(self) -> None:
        await self.__splash_screen()
        await asyncio.sleep(2)

        await self.__clean_screen()

        logging.info("Display setup complete")

        self._subscriber.add_async_listener(self._subscribe_key, self.__on_new_tag)

    # Private methods

    async def __setup_productview_frame(self) -> None:
        def setup_ui_frame():
            self._draw.rectangle((0, 16, self.width-1, self.height-1), outline=True, fill=False)
            self._draw.line((0, 16, 127, 16), fill=True)
            self._oled.image(self._image)

        await self._loop.run_in_executor(None, setup_ui_frame)

    async def __on_new_tag(self, key, product: Product) -> None:
        logging.debug("New message with key: %s", key)
        await self.__configure_product_view(product.name, product.price, product.expiration_day.strftime("%d/%m/%y"), product.product_id)

    async def __splash_screen(self) -> None:
        await self.__setup_productview_frame()
        await self.__write_text((12, 20), "Smart shelf", font=font_18)
        await self.__write_text((32, 45), "Loading...")
        await self.__show_screen()

    async def __configure_product_view(self, product: str, price: float, eol: str, id: str) -> None:
        prc = format(price, ".2f")
        await self.__clean_screen()
        await self.__setup_productview_frame()
        await self.__write_text((2, 1), product)
        await self.__write_text((5, 16), f"{prc} \u20ac", font=font_18)
        await self.__write_text((5, 34), f"Art.: {id}")
        await self.__write_text((5, 47), f"Scad.: {eol}")
        await self.__show_screen()

    async def __show_screen(self):
        def show():
            self._oled.show()
        await self._loop.run_in_executor(None, show)

    async def __write_text(self, pos: Tuple[int, int], text: str, font = font_12) -> None:
        def callback():
            self._draw.text(pos, text, font=font, fill=255)
            self._oled.image(self._image)

        await self._loop.run_in_executor(None, callback)

    async def __clean_screen(self) -> None:
        def callback():
            self._draw.rectangle((0, 0, self._oled.width, self._oled.height), 0, 0)
            self._oled.image(self._image)
            self._oled.show()

        await self._loop.run_in_executor(None, callback)
