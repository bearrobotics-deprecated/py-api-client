# Bear Python API Client
This is a simple Python client program to demonstrate using AMQP-based Bear Robotics mission API. This implementation is done in Python3 but client programs can implemented in any programming language as long as they follow the AMQP protocol.

# Installing the client
Client can be installed using `pip`.

```sh
 $ python -m pip install git+https://gitlab.com/bearrobotics-public/py-api-client.git
```


## Running the client
To run the client, we need to provide the robot Id that we wish to control/monitor, as well as RabbitMQ server address information and authentication method. The client app will connect to port 5672 in HTTP based and port 5671 in TLS mode. You can use `--help` flag to see an overview of the supported parameters.

The client can run in two modes: (1) `rpc`, when it sends a command to the robot and prints the response on the console (and then terminates), and (2) `subscribe` mode, where it subscribes to events from a particular robot and print any change in robot status on the console indefinitely.

```sh
 $ py-api-client --help
 usage: main.py [-h] --addr ADDR [--user USER] [--password PASSWORD] --vhost
               VHOST [--cert_path CERT_PATH] --robot_id ROBOT_ID --mode
               {subscribe,rpc} [--func FUNC] [--log_level LOG_LEVEL]

optional arguments:
  -h, --help            show this help message and exit
  --addr ADDR           URL address of RabbitMQ server
  --user USER           Rabbitmq user
  --password PASSWORD   password
  --vhost VHOST         virtual host to connect to
  --cert_path CERT_PATH
                        Certificate path
  --robot_id ROBOT_ID   Robot ID
  --mode {subscribe,rpc}
                        Operation mode
  --func FUNC           RPC function
  --log_level LOG_LEVEL
                        logging level like INFO
```

### Authenticate with plain text
To authenticate the client using user/password, use `user` and `pass` flags.
```sh
 $ py-api-client --robot_id pennybot_abc123 --mode subscribe --user user --pass pass --addr serverURL --vhost vhost
```
### Authenticate with certificates
To authenticate the client with certifciates, use `cert_path` pointing to folder where they are stored.
```sh
 $ py-api-client --robot_id pennybot_abc123 --mode subscribe --addr serverURL --cert_path path --vhost vhost
```

### Sending commands to tray mission service
The Client can send commands to the mission service running on the robot in the form of remote procedure call (RPC). To do that client sends a command message to `$robot_id` exchnage on the RabbitMQ server and wait for the response from the robot. Server will transfer the message to the robot and will redirect its response to client. Matching the response with the right request is done using message fields: "Reply To" (where), and "Correlation ID" (which).

`Caller` class in `amqp.py` abstracts this sequence of operations.

#### Sample commands:
Here are few sample commands that is understood by the Robots. Note that there should not be any whitespaces in `--func` argument.

1. Getting lists of destinations
```sh
 $ py-api-client  --mode rpc --func '{"cmd":"/api/2/get/destinations"}' $OTHER_ARGS
```
2. Sending a new mission
```sh
 $ py-api-client --mode rpc --func\
 '{"cmd":"/api/2/post/mission/new","args":{"destinations":["T1","T2"],\
 "trays":[{"name":"top","destination":"T1"},{"name":"middle","destination":"T2"}],"mode":"Serving"}}' $OTHER_ARGS
```
3. Getting mission status
```sh
 $ py-api-client --mode rpc --func '{"cmd":"/api/2/get/mission/status"}' $OTHER_ARGS
```
4. Canceling the current mission
```sh
 $ py-api-client --mode rpc --func '{"cmd":"/api/2/post/mission/cancel"}' $OTHER_ARGS
```


### Getting mission/tray updates
RabbitMQ server manages the message delivery via various exchanges. In a working communication, both sender and receiver must know and agree upon the exchange topology in advance.

In the current implementation the clients can register callbacks to following exchanges that robots use to publish robot/mission updates:

1. `$robot_id/mission_update` for updates to current mission status
2. `$robot_id/trays_update` for updates to trays status
2. `$robot_id/status` for updates to robot status
