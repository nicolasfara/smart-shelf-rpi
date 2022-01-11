import asyncio
import logging
from typing import Tuple

import adafruit_ssd1306
import aiopubsub
import board
from PIL import Image, ImageDraw, ImageFont

font_12 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
font_24 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)

class Display:

    def __init__(self, loop: asyncio.AbstractEventLoop, message_bus: aiopubsub.Hub) -> None:
        self._i2c = board.I2C()
        self._oled = adafruit_ssd1306.SSD1306_I2C(128, 32, self._i2c, addr=0x3c)

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

    async def __on_new_tag(self, key, message) -> None:
        await self.__write_text((0, 0), message)

    async def __splash_screen(self) -> None:
        await self.__write_text((0, 0), "Smart shelf\nLoading...")

    async def __write_text(self, pos: Tuple[int, int], text: str, font = font_12) -> None:
        await self.__clean_screen()

        def callback():
            self._draw.text(pos, text, font=font, fill=255)
            self._oled.image(self._image)
            self._oled.show()

        await self._loop.run_in_executor(None, callback)

    async def __clean_screen(self) -> None:
        def callback():
            self._draw.rectangle((0, 0, self._oled.width, self._oled.height), 0, 0)
            self._oled.image(self._image)
            self._oled.show()

        await self._loop.run_in_executor(None, callback)
