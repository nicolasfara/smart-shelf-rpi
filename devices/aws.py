"""
Class managing AWS connection.
"""
import asyncio
import json
import logging
import sys

import aiopubsub
from awscrt import io, mqtt
from awsiot import mqtt_connection_builder

from models.product import Product


class AwsDevice:
    """
    Aws device.
    """
    def __init__(
        self,
        endpoint: str,
        root_ca: str,
        cert: str,
        key: str,
        client_id: str,
        message_bus: aiopubsub.Hub
    ) -> None:
        self.__endpoint = endpoint
        self.__client_id = client_id
        self.__message_bus = message_bus
        self.__subscriber = aiopubsub.Subscriber(self.__message_bus, "aws")
        self.__subscribe_key = aiopubsub.Key("*", "tag", "*")

        self.__logger = logging.getLogger("aws")

        event_loop_group = io.EventLoopGroup(1)
        host_resolver = io.DefaultHostResolver(event_loop_group)
        client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)

        self.__mqtt_connection = mqtt_connection_builder.mtls_from_path(
            endpoint=endpoint,
            cert_filepath=cert,
            pri_key_filepath=key,
            client_bootstrap=client_bootstrap,
            ca_filepath=root_ca,
            on_connection_interrupted=self.__on_connection_interrupted,
            on_connection_resumed=self.__on_connection_resumed,
            client_id=client_id,
            clean_session=False,
            keep_alive_secs=30,
        )

    async def start(self):
        """
        TODO.
        """
        self.__logger.debug("Connecting to %s with client id %s", self.__endpoint, self.__client_id)
        await asyncio.wrap_future(self.__mqtt_connection.connect())
        self.__logger.debug("Connected to %s", self.__endpoint)

        self.__subscriber.add_async_listener(self.__subscribe_key, self.__on_new_tag)

    async def stop(self):
        """
        TODO.
        """
        await asyncio.wrap_future(self.__mqtt_connection.disconnect())
        self.__logger.info("Disconnect from %s", self.__endpoint)

    # Private methods

    async def __on_new_tag(self, key, product: Product) -> None:
        self.__logger.debug("Got new message with key %s: %s", key, product)
        self.__mqtt_connection.publish(
            topic="test/topic",
            payload=json.dumps(product),
            qos=mqtt.QoS.AT_LEAST_ONCE
        )

    def __on_connection_interrupted(self, connection, error, **kwargs) -> None:
        #pylint: disable=unused-argument
        self.__logger.error("Connection %s interrupted. error: %s", connection, error)

    def __on_connection_resumed(self, connection, return_code, session_present, **kwargs) -> None:
        #pylint: disable=unused-argument
        self.__logger.warning("Connection resumed. return_code: %s session_present: %s", return_code, session_present)

        if return_code == mqtt.ConnectReturnCode.ACCEPTED and not session_present:
            self.__logger.warning("Session did not persist. Resubscribing to existing topics...")
            resubscribe_future, _ = connection.resubscribe_existing_topics()

            # Cannot synchronously wait for resubscribe result because we're on the connection's event-loop thread,
            # evaluate result with a callback instead.
            resubscribe_future.add_done_callback(self.__on_resubscribe_complete)

    def __on_resubscribe_complete(self, resubscribe_future):
        resubscribe_results = resubscribe_future.result()
        self.__logger.debug("Resubscribe results: %s", resubscribe_results)

        for topic, qos in resubscribe_results['topics']:
            if qos is None:
                sys.exit(f"Server rejected resubscribe to topic: {topic}")
