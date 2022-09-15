"""The Python implementation of a simple AMQP client program for BearRobotics
   mission API.

1. Sending a command to the robot
$ py-api-client --addr $ADDR --vhost $VHOST --mode rpc --robot_id $ROBOT_ID \
  --cert_path $CERT_TO_PATH --func '{"cmd":"/api/2/get/mission/status"}'

2. Subscribing to robot updates
$ py-api-client --addr $ADDR --vhost $VHOST --mode subscribe \
  --robot_id $ROBOT_ID --cert_path $CERT_PATH

"""

import argparse
import json
import logging
import threading

from client import amqp

MISSION_UPDATE_TOPIC = "mission_update"
TRAYS_UPDATE_TOPIC = "trays_update"
STATUS_TOPIC = "status"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--addr',
        help='Address of RabbitMQ server in format of url:port',
        required=True,
    )
    parser.add_argument(
        '--user',
        help='Rabbitmq user',
        required=False,
    )
    parser.add_argument(
        '--password',
        help='password',
        required=False,
    )
    parser.add_argument('--vhost',
                        help='virtual host to connect to',
                        required=True)
    parser.add_argument(
        '--cert_path',
        help='Certificate path',
        required=False,
    )
    parser.add_argument(
        '--robot_id',
        help='Robot ID',
        required=True,
    )
    parser.add_argument(
        '--mode',
        choices=['subscribe', 'rpc'],
        help='Operation mode',
        required=True,
    )
    parser.add_argument(
        '--func',
        help="RPC function",
        required=False,
    )
    parser.add_argument(
        '--log_level',
        default='INFO',
        help='logging level like INFO',
    )
    return parser.parse_args()


def connect(addr, user, password, vhost, cert_path, open_callback, blocking):
    if user and password:
        return amqp.dial_tcp(addr, user, password, vhost, open_callback,
                             blocking)
    return amqp.dial_tls(addr, cert_path, vhost, open_callback, blocking)


def print_update(ch, method, properties, body):
    print(json.dumps(json.loads(body), indent=1))


def main():
    args = parse_args()
    logging.basicConfig(
        format='[%(levelname)s] %(asctime)-15s %(message)s',
        level=args.log_level,
    )

    if args.mode == "subscribe":
        topics = [
            "{0}/{1}".format(args.robot_id, topic) for topic in [
                MISSION_UPDATE_TOPIC,
                TRAYS_UPDATE_TOPIC,
                STATUS_TOPIC,
            ]
        ]

        subs = [
            amqp.AsyncSubscriber(topic, print_update, logging)
            for topic in topics
        ]

        def on_channel_open(channel):
            logging.debug("Channel opened.")
            for sub in subs:
                sub.start(channel)

        def on_open(connection):
            logging.debug("Connection opened.")
            connection.channel(on_open_callback=on_channel_open)

        try:
            conn = connect(args.addr, args.user, args.password, args.vhost,
                           args.cert_path, on_open, False)
            logging.info("Started.")
            conn.ioloop.start()
        except KeyboardInterrupt:
            logging.debug("Closing connection.")
            conn.close()
            conn.ioloop.start()

    else:  # RPC
        conn = connect(args.addr, args.user, args.password, args.vhost,
                       args.cert_path, None, True)
        caller = amqp.Caller(conn)
        result = caller.call(args.robot_id, args.func, 1)
        if result:
            print(json.dumps(json.loads(result), indent=1))
        conn.close()


if __name__ == '__main__':
    main()
