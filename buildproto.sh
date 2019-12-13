#! /bin/bash
cp example-service/service/service_spec/*.proto protos/
python3 -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. ./protos/example_service.proto
