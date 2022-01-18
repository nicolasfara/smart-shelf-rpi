"""
TODO.
"""
import argparse
import asyncio
import logging
import os
import signal
import sys
from uuid import uuid4

import aiopubsub
from dotenv import load_dotenv

from devices.aws import AwsDevice
from devices.display import Display
from devices.rfid_reader import RfidReader

load_dotenv()

parser = argparse.ArgumentParser()
parser.add_argument("--dryrun", help="Disabele connection with AWS, no messages are sent", action="store_true")
args = parser.parse_args()

try:
    aws_endpoint = os.environ["AWS_ENDPOINT"]
    aws_root_ca = os.environ["AWS_ROOT_CA"]
    aws_cert = os.environ["AWS_CERT"]
    aws_key = os.environ["AWS_KEY"]
    client_id = os.getenv("CLIENT_ID", f"test-{str(uuid4())}")
except KeyError as e:
    print("Unable to get the env variable:", e)
    sys.exit(1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    loop = asyncio.get_event_loop()
    message_bus = aiopubsub.Hub()

    display = Display(loop=loop, message_bus=message_bus)
    rfid_reader = RfidReader(loop=loop, message_bus=message_bus)
    if not args.dryrun:
        aws_device = AwsDevice(
            endpoint=aws_endpoint,
            root_ca=aws_root_ca,
            cert=aws_cert,
            key=aws_key,
            client_id=client_id,
            message_bus=message_bus
        )

    async def __on_quit():
        if not args.dryrun:
            await aws_device.stop()
        loop.stop()

    loop.add_signal_handler(signal.SIGINT, lambda: asyncio.create_task(__on_quit()))

    task1 = asyncio.Task(display.start_display())
    task2 = asyncio.Task(rfid_reader.start_reading())
    if not args.dryrun:
        task3 = asyncio.Task(aws_device.start())

    logging.info("Staring...")
    loop.run_forever()
