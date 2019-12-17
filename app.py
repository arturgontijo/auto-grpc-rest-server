import sys
from pathlib import Path
import traceback

from flask import Flask, request
import grpc

PROJECT_DIR = Path(__file__).absolute().parent
sys.path.insert(0, "{}".format(PROJECT_DIR))
from utils.proto_tools import load_proto, input_factory, output_factory

SERVER_HOST = "0.0.0.0"
SERVER_PORT = 7000
GRPC_HOST = "0.0.0.0"
GRPC_PORT = 7003

# Open a gRPC channel
CHANNEL = grpc.insecure_channel("{}:{}".format(GRPC_HOST, GRPC_PORT))

app = Flask(__name__)


@app.route("/", methods=["POST"])
@app.route("/<path:path>", methods=["POST"])
def rest_to_grpc(path=None):
    if request.method == "POST":
        try:
            if not path:
                return services_dict

            path_list = path.split("/")
            if not path_list or path_list[0].upper() == "HELP":
                return services_dict

            service = path_list[0]
            if not service or service not in services_dict:
                return {"Error": "Invalid gRPC service.", **services_dict}

            if len(path_list) > 1:
                method = path_list[1]
            else:
                method = request.json.get("method", list(services_dict[service].keys())[0])

            if method not in services_dict[service].keys():
                return {"Error": "Invalid gRPC method.", **services_dict[service]}

            input_message = services_dict[service][method]["input"]
            input_dict = input_factory(request.json, input_message, classes)

            grpc_input = classes[input_message["name"]](**input_dict)

            stub = stubs[service](CHANNEL) if stubs[service] else None
            method_stub = getattr(stub, method, None)
            response = method_stub(grpc_input)

            output_message = services_dict[service][method]["output"]
            output_dict = output_factory(response, output_message)
            return output_dict, 200

        except Exception as e:
            print("{}\n{}".format(e, traceback.print_exc()))
            return {"Error": "Invalid gRPC request.", **services_dict}
        
    return {"Error": "Invalid HTTP request."}


pb_list, pb_grpc_list, services_dict, classes, stubs = load_proto("./protos")

app.run(debug=False,
        host=SERVER_HOST,
        port=SERVER_PORT,
        use_reloader=False,
        threaded=True,
        passthrough_errors=True)
