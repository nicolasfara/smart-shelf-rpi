"""
Class for managing RFID operations.
"""

import asyncio
import logging
from typing import Union

import aiopubsub
import board
from adafruit_pn532.adafruit_pn532 import MIFARE_CMD_AUTH_B
from adafruit_pn532.i2c import PN532_I2C

from models.product import ProductTag


class RfidReader:
    """
    Mange all the tag reading.
    """
    def __init__(self, loop: asyncio.AbstractEventLoop, message_bus: aiopubsub.Hub, debug = False):
        """
        Setup RFID reader.
        This class is async, an event loop should be given.
        A queue is used to share tag's data with other subscribers.
        """
        self._pn532 = PN532_I2C(board.I2C(), debug=debug)
        self._auth_key = b"\xFF\xFF\xFF\xFF\xFF\xFF"

        # Configure RFID module
        self._pn532.SAM_configuration()
        self._loop = loop
        self._message_bus = message_bus
        self._publisher = aiopubsub.Publisher(self._message_bus, prefix = aiopubsub.Key("reader"))
        self._publish_key = aiopubsub.Key("tag", "product")
        self.__logger = logging.getLogger("RFID")


    async def start_reading(self) -> None:
        """
        Start reading tags.
        """
        logging.debug("Start reading new tags")

        while True:
            uid = await self._loop.run_in_executor(None, self._pn532.read_passive_target)
            if uid is not None:
                self.__logger.debug("New card found: %s", uid.hex())

                code = await self.__read_sector(uid, 1)
                lot = await self.__read_sector(uid, 2)

                if code is not None and lot is not None:
                    self.__logger.info("Read 'code' and 'lot' successfully")
                    self.__logger.info("Code: %s", code.decode())
                    self.__logger.info("Lot: %s", lot.decode())
                    self.__logger.debug("Code bytes: %s", [hex(x) for x in code])
                    self.__logger.debug("Lot bytes: %s", [hex(x) for x in lot])

                    product = ProductTag(
                        id=uid.hex(),
                        code=code.decode(),
                        lot=int(lot.decode()),
                    )
                    self._publisher.publish(self._publish_key, product)

                    await asyncio.sleep(0.5)

    async def __read_block(self, uid, block: int) -> Union[bytearray, None]:
        """
        Read the given block from the tag with the given UID.
        """
        auth = await self._loop.run_in_executor(
            None,
            self._pn532.mifare_classic_authenticate_block,
            uid,
            block,
            MIFARE_CMD_AUTH_B,
            self._auth_key
        )
        if not auth:
            self.__logger.error("Authentication failed: block %d, auth: %s", block, self._auth_key)

        return await self._loop.run_in_executor(None, self._pn532.mifare_classic_read_block, block)

    async def __read_sector(self, uid, sector: int) -> Union[bytearray, None]:
        """
        Read the given sector from the tag with the given UID.
        This method read only data block, the authentication block is ignored.
        """
        start_block = sector * 4
        res = bytearray(0)
        for blk in range(0, 3):
            block = await self.__read_block(uid, start_block + blk)
            if block is None:
                self.__logger.error("Fail to read block %d", start_block + blk)
                return None
            res.extend(block)
        return res
