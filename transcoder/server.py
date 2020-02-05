import sys
import json
from pathlib import Path
import traceback

import grpc
from grpc_health.v1 import health_pb2_grpc as heartb_pb2_grpc
from grpc_health.v1 import health_pb2 as heartb_pb2

from flask import Flask, request

TRANSCODER_DIR = Path(__file__).absolute().parent
sys.path.insert(0, "{}".format(TRANSCODER_DIR))
from utils.proto_tools import input_factory, output_factory


class TranscoderServer:
    def __init__(self,
                 host, port,
                 ssl_context,
                 services_dict, classes, stubs,
                 grpc_host, grpc_port,
                 grpc_check=False,
                 custom_check=None,
                 use_cors=False):

        self.app = Flask(__name__)
        self.host = host
        self.port = port
        self.ssl_context = ssl_context
        self.services_dict = services_dict
        self.classes = classes
        self.stubs = stubs
        self.grpc_host = grpc_host
        self.grpc_port = grpc_port

        if use_cors:
            from flask_cors import CORS
            CORS(self.app)

        # checking if the gRPC server is up and running
        if custom_check:
            check_input = json.loads(custom_check)
            self.check(check_input)
        elif grpc_check:
            self.grpc_health_check()

    def check(self, check_input):
        service = list(self.services_dict.keys())[0]
        method = list(self.services_dict[service].keys())[0]
        input_message = self.services_dict[service][method]["input"]
        grpc_input = self.classes[input_message["name"]](**check_input)
        with grpc.insecure_channel("{}:{}".format(self.grpc_host, self.grpc_port)) as channel:
            stub = self.stubs[service](channel) if self.stubs[service] else None
            method_stub = getattr(stub, method, None)
            method_stub(grpc_input)

    def grpc_health_check(self):
        channel = grpc.insecure_channel("{}:{}".format(self.grpc_host, self.grpc_port))
        stub = heartb_pb2_grpc.HealthStub(channel)
        stub.Check(heartb_pb2.HealthCheckRequest(service=""), timeout=10)

    def serve(self):
        @self.app.route("/", methods=["GET", "POST"])
        @self.app.route("/<path:path>", methods=["GET", "POST"])
        def rest_to_grpc(path=None):
            if request.method in ["GET", "POST"]:
                try:
                    req = None
                    if request.method == "GET":
                        if not request.args:
                            ret = dict()
                            for s in self.services_dict.keys():
                                ret[s] = list(self.services_dict[s].keys())
                            return ret, 200
                        else:
                            req = request.args.to_dict()

                    if not path:
                        return self.services_dict, 500

                    path_list = path.split("/")
                    if not path_list or path_list[0].upper() == "HELP":
                        return self.services_dict, 500

                    service = path_list[0]
                    if service not in self.services_dict:
                        return {"Error": "Invalid gRPC service.", **self.services_dict}, 500

                    if not req:
                        if request.data:
                            req = json.loads(request.data.decode("utf-8"))
                        else:
                            req = request.json if request.json else request.form.to_dict()

                    if len(path_list) > 1:
                        method = path_list[1]
                    else:
                        method = req.get("method", list(self.services_dict[service].keys())[0])

                    if method not in self.services_dict[service].keys():
                        return {"Error": "Invalid gRPC method.", **self.services_dict[service]}, 500

                    input_message = self.services_dict[service][method]["input"]
                    input_dict = input_factory(req, input_message, self.classes)

                    grpc_input = self.classes[input_message["name"]](**input_dict)

                    with grpc.insecure_channel("{}:{}".format(self.grpc_host, self.grpc_port)) as channel:
                        stub = self.stubs[service](channel) if self.stubs[service] else None
                        method_stub = getattr(stub, method, None)
                        response = method_stub(grpc_input)
                        output_message = self.services_dict[service][method]["output"]
                        output_dict = output_factory(response, output_message)

                    return output_dict, 200

                except Exception as e:
                    print("{}\n{}".format(e, traceback.print_exc()))
                    return {"Error": "Invalid gRPC request.", **self.services_dict}, 500

            return {"Error": "Invalid HTTP request (use POST)."}, 500

        self.app.run(debug=False,
                     host=self.host,
                     port=self.port,
                     ssl_context=self.ssl_context,
                     use_reloader=False,
                     threaded=True,
                     passthrough_errors=True)
