"""
Class managing AWS connection.
"""
import asyncio
import json
import logging
import sys

import aiopubsub
from awscrt import auth, http, io, mqtt
from awsiot import iotshadow, mqtt_connection_builder

from models.product import Product


class AwsDevice:
    def __init__(
        self,
        endpoint: str,
        root_ca: str,
        cert: str,
        key: str,
        client_id: str,
        message_bus: aiopubsub.Hub
    ) -> None:
        self._endpoint = endpoint
        self._root_ca = root_ca
        self._cert = cert
        self._key = key
        self._client_id = client_id
        self._message_bus = message_bus
        self._subscriber = aiopubsub.Subscriber(self._message_bus, "aws")
        self._subscribe_key = aiopubsub.Key("*", "tag", "*")

        event_loop_group = io.EventLoopGroup(1)
        host_resolver = io.DefaultHostResolver(event_loop_group)
        client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)

        self._mqtt_connection = mqtt_connection_builder.mtls_from_path(
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
        logging.debug("Connecting to %s with client id %s", self._endpoint, self._client_id)
        await asyncio.wrap_future(self._mqtt_connection.connect())
        logging.debug("Connected to %s", self._endpoint)

        self._subscriber.add_async_listener(self._subscribe_key, self.__on_new_tag)

    async def stop(self):
        await asyncio.wrap_future(self._mqtt_connection.disconnect())
        logging.info("Disconnect from %s", self._endpoint)

    # Private methods

    async def __on_new_tag(self, key, product: Product) -> None:
        logging.debug("Publish %s", product)
        self._mqtt_connection.publish(
            topic="test/topic",
            payload=json.dumps(product),
            qos=mqtt.QoS.AT_LEAST_ONCE
        )

    def __on_connection_interrupted(self, connection, error, **kwargs) -> None:
        logging.error("Connection interrupted. error: %s", error)

    def __on_connection_resumed(self, connection, return_code, session_present, **kwargs) -> None:
        logging.warn("Connection resumed. return_code: %s session_present: %s", return_code, session_present)

        if return_code == mqtt.ConnectReturnCode.ACCEPTED and not session_present:
            logging.warn("Session did not persist. Resubscribing to existing topics...")
            resubscribe_future, _ = connection.resubscribe_existing_topics()

            # Cannot synchronously wait for resubscribe result because we're on the connection's event-loop thread,
            # evaluate result with a callback instead.
            resubscribe_future.add_done_callback(self.__on_resubscribe_complete)

    def __on_resubscribe_complete(self, resubscribe_future):
        resubscribe_results = resubscribe_future.result()
        logging.debug("Resubscribe results: %s", resubscribe_results)

        for topic, qos in resubscribe_results['topics']:
            if qos is None:
                sys.exit("Server rejected resubscribe to topic: {}".format(topic))
