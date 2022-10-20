"""Module amqp provides primitives to communicate with Bear AMQP message broker.
"""

import logging
import ssl
import uuid
import os

import pika
from cryptography import x509


def get_new_queue_params():
    return {
        'x-message-ttl': 5000,
        'x-max-length': 10,
        'x-max-length-bytes': 16 * 1024,
    }


def dial_tcp(host, username, password, vhost, callback, blocking=True):
    credentials = pika.credentials.PlainCredentials(username,
                                                    password,
                                                    erase_on_connect=False)
    params = pika.ConnectionParameters(host=host,
                                       port=5672,
                                       virtual_host=vhost,
                                       credentials=credentials)
    if blocking:
        return pika.BlockingConnection(parameters=params)
    return pika.SelectConnection(parameters=params, on_open_callback=callback)


def dial_tls(host, cert_path, vhost, callback, blocking=True):
    params = tls_config(host, 5671, vhost, cert_path)
    if blocking:
        return pika.BlockingConnection(parameters=params)
    return pika.SelectConnection(parameters=params, on_open_callback=callback)


def tls_config(host, port, vhost, cert_path):
    context = ssl.create_default_context(
        cafile=os.path.join(cert_path, "ca_certificate.pem"))
    context.load_cert_chain(os.path.join(cert_path, "certificate.pem"),
                            os.path.join(cert_path, "key.pem"))
    ssl_options = pika.SSLOptions(context)
    return pika.ConnectionParameters(
        host=host,
        port=port,
        virtual_host=vhost,
        ssl_options=ssl_options,
        credentials=pika.credentials.ExternalCredentials())


class Caller:
    """Calls a function on a Bear robot running mission service and collectes
       the response.
    """

    def __init__(self, connection):
        self._connection = connection
        self._channel = self._connection.channel()

        result = self._channel.queue_declare(queue='',
                                             exclusive=True,
                                             durable=False,
                                             auto_delete=True,
                                             arguments=get_new_queue_params())

        self._callback_queue = result.method.queue

        self._channel.basic_consume(queue=self._callback_queue,
                                    on_message_callback=self._on_response,
                                    auto_ack=True)

        self._response = None
        self._corr_id = None

    def _on_response(self, ch, method, props, body):
        if self._corr_id == props.correlation_id:
            self._response = body

    def call(self, robot_id, command, timeout):
        """Sends a command to a robot and returns the collected repsonse.

        Args:
            robot_id: Robot ID to send command to.
            command: JSON representation of the command.
            timeout: Call timeout value in seconds.
        """
        self._response = None
        self._corr_id = str(uuid.uuid4())
        self._channel.basic_publish(exchange='',
                                    routing_key=robot_id,
                                    properties=pika.BasicProperties(
                                        reply_to=self._callback_queue,
                                        correlation_id=self._corr_id,
                                    ),
                                    body=command)
        self._connection.process_data_events(time_limit=timeout)
        return self._response


class AsyncSubscriber:
    """Subscribes to updates from a Bear robot running mission service."""

    def __init__(self, topic, callback, logger):
        self._topic = topic
        self._callback = callback
        self._logger = logger

    def _on_exchange_declared(self, _):
        result = self._channel.queue_declare(queue='',
                                             exclusive=True,
                                             durable=False,
                                             auto_delete=True,
                                             arguments=get_new_queue_params(),
                                             callback=self._on_queue_declared)

    def _on_queue_declared(self, frame):
        self._queue_name = frame.method.queue
        self._channel.queue_bind(exchange=self._topic,
                                 queue=self._queue_name,
                                 callback=self._on_queue_bind)

    def _on_message(self, ch, method, properties, body):
        self._callback(ch, method, properties, body)

    def _on_consume_ok(self, _):
        self._logger.info("Started consuming {0}!".format(self._topic))

    def _on_queue_bind(self, _):
        self._channel.basic_consume(queue=self._queue_name,
                                    auto_ack=True,
                                    on_message_callback=self._on_message,
                                    callback=self._on_consume_ok)

    def start(self, channel):
        """Starts subscribing to the provided topic. It will invoke callback
           method upon receiving every message from the mesage broker.

        Args:
            channel: Opened AMQP channel to the RabbitMQ broker. channel can be
            shared safely between multiple instancs of AsyncSubscriber.
        """
        self._channel = channel
        self._channel.exchange_declare(exchange=self._topic,
                                       exchange_type='fanout',
                                       durable=True,
                                       passive=True,
                                       callback=self._on_exchange_declared)
