# simple-transcoder
Python tool to interface a gRPC API and a REST API, using JSON on requests and responses.

First clone this repo:
```shell script
git clone https://github.com/arturgontijo/simple-transcoder.git
cd simple-transcoder
```

Installing the dependencies:
```shell script
pip3 install -r requirements.txt
```

Starting the gRPC API at `example-service` (from SingularityNET):
```shell script
cd example-service
sh buildproto.sh
python3 run_example_service.py --no-daemon
```

This gRPC server uses the following `.proto`, it's just a simple calculator:

```proto
syntax = "proto3";

package example_service;

message Numbers {
    float a = 1;
    float b = 2;
}

message Result {
    float value = 1;
}

service Calculator {
    rpc add(Numbers) returns (Result) {}
    rpc sub(Numbers) returns (Result) {}
    rpc mul(Numbers) returns (Result) {}
    rpc div(Numbers) returns (Result) {}
}
```

In a new terminal window, let's copy this `.proto` into an appropriate directory:
```shell script
cd ..
mkdir protos
cp example-service/service/service_spec/example_service.proto protos/
```

Next step is to launch the `simple-transcoder`:
```shell script
python3 transcoder --proto-dir protos
```

In a third terminal window, let's test the interface:

```shell script
curl -XPOST -H "Content-Type: application/json" -d '{"a": 9, "b": 8}' localhost:7000/Calculator/add
{"value":17.0}

curl -XPOST -H "Content-Type: application/json" -d '{"a": 9, "b": 8}' localhost:7000/Calculator/sub
{"value":1.0}

curl -XPOST -H "Content-Type: application/json" -d '{"a": 9, "b": 8}' localhost:7000/Calculator/mul
{"value":72}

curl -XPOST -H "Content-Type: application/json" -d '{"a": 9, "b": 8}' localhost:7000/Calculator/div
{"value":1.125}

curl -XPOST -H "Content-Type: application/json" -d '{"a": 9, "b": 8}' localhost:7000/Calculator/invalid
{"Error":"Invalid gRPC method.","add":{"input":{"fields":{"a":{"label":1,"type":2},"b":{"label":1,"type":2}},"name":"Numbers"},"output":{"fields":{"value":{"label":1,"type":2}},"name":"Result"}},"div":{"input":{"fields":{"a":{"label":1,"type":2},"b":{"label":1,"type":2}},"name":"Numbers"},"output":{"fields":{"value":{"label":1,"type":2}},"name":"Result"}},"mul":{"input":{"fields":{"a":{"label":1,"type":2},"b":{"label":1,"type":2}},"name":"Numbers"},"output":{"fields":{"value":{"label":1,"type":2}},"name":"Result"}},"sub":{"input":{"fields":{"a":{"label":1,"type":2},"b":{"label":1,"type":2}},"name":"Numbers"},"output":{"fields":{"value":{"label":1,"type":2}},"name":"Result"}}}
```

