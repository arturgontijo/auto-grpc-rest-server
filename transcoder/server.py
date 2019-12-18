import sys
import json
from pathlib import Path
import traceback

from flask import Flask, request

TRANSCODER_DIR = Path(__file__).absolute().parent
sys.path.insert(0, "{}".format(TRANSCODER_DIR))
from utils.proto_tools import input_factory, output_factory


class TranscoderServer:
    def __init__(self, host, port, services_dict, classes, stubs, channel):
        self.app = Flask(__name__)
        self.host = host
        self.port = port
        self.services_dict = services_dict
        self.classes = classes
        self.stubs = stubs
        self.channel = channel

    def serve(self):
        @self.app.route("/", methods=["POST"])
        @self.app.route("/<path:path>", methods=["POST"])
        def rest_to_grpc(path=None):
            if request.method == "POST":
                try:
                    if not path:
                        return self.services_dict, 500
        
                    path_list = path.split("/")
                    if not path_list or path_list[0].upper() == "HELP":
                        return self.services_dict, 500
        
                    service = path_list[0]
                    if service not in self.services_dict:
                        return {"Error": "Invalid gRPC service.", **self.services_dict}, 500
                    
                    if request.data:
                        req = json.loads(request.data)
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
        
                    stub = self.stubs[service](self.channel) if self.stubs[service] else None
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
                     use_reloader=False,
                     threaded=True,
                     passthrough_errors=True)
