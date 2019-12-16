import sys
import json
from pathlib import Path
import traceback

from flask import Flask, request
import grpc

from google.protobuf.descriptor import FieldDescriptor as FD

PROJECT_DIR = Path(__file__).absolute().parent
sys.path.insert(0, "{}".format(PROJECT_DIR))
# import the generated classes
# import protos.example_service_pb2_grpc as pb_grpc
# import protos.example_service_pb2 as pb

import protos.face_landmarks_pb2_grpc as pb_grpc
import protos.face_landmarks_pb2 as pb

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
    services_dict = load_proto()
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
    
            stub = getattr(pb_grpc, "{}Stub".format(service), None)
            if stub:
                stub = stub(CHANNEL)
    
            # input_message = services_dict[service][method]["input"]
            # input_dict = dict()
            # for f in input_message["fields"].keys():
            #     var_type = input_message['fields'][f]['type']
            #     tmp_var = request.json.get(f, None)
            #     input_dict[f] = type_converter(tmp_var, var_type) if tmp_var else None

            input_message = services_dict[service][method]["input"]
            classes = dict()
            get_classes(pb, classes)
            input_dict = dict()
            input_dict = message_factory(request.json, input_message, classes)
            print("input_dict:", input_dict)

            grpc_input = classes[input_message["name"]]
            grpc_input = grpc_input(**input_dict)

            method_stub = getattr(stub, method, None)
            response = method_stub(grpc_input)
    
            output_message = services_dict[service][method]["output"]
            output_variables_dict = dict()
            for f in output_message["fields"].keys():
                output_variables_dict[f] = getattr(response, f, None)
            return output_variables_dict, 200
        except Exception as e:
            print("{}\n{}".format(e, traceback.print_exc()))
            return {"Error": "Invalid gRPC request.", **services_dict}
    return {"Error": "Invalid HTTP request."}


def type_converter(value, conversion_type):
    conversion_func = {
        FD.TYPE_DOUBLE: float,
        FD.TYPE_FLOAT: float,
        FD.TYPE_INT64: int,
        FD.TYPE_UINT64: int,
        FD.TYPE_INT32: int,
        FD.TYPE_FIXED64: float,
        FD.TYPE_FIXED32: float,
        FD.TYPE_BOOL: bool,
        FD.TYPE_STRING: str,
        # FD.TYPE_MESSAGE: pass
        FD.TYPE_BYTES: lambda x: str(x).encode(),
        FD.TYPE_UINT32: int,
        FD.TYPE_ENUM: int,
        FD.TYPE_SFIXED32: float,
        FD.TYPE_SFIXED64: float,
        FD.TYPE_SINT32: int,
        FD.TYPE_SINT64: int,
    }
    try:
        value = conversion_func[conversion_type](value)
    except Exception as e:
        print(e)
    return value


def load_proto():
    def get_nested_messages(_input_message):
        ret = dict()
        for _f in _input_message.fields_by_name.keys():
            if _input_message.fields_by_name[_f].message_type:
                ret[_f] = {
                    "name": _input_message.fields_by_name[_f].message_type.name,
                    "label": _input_message.fields_by_name[_f].label,
                    "type": _input_message.fields_by_name[_f].type
                }
                ret[_f]["fields"] = get_nested_messages(_input_message.fields_by_name[_f].message_type)
            else:
                ret[_f] = {
                    "label": _input_message.fields_by_name[_f].label,
                    "type": _input_message.fields_by_name[_f].type
                }
        return ret
    services = pb.DESCRIPTOR.services_by_name.keys()
    services_dict = dict()
    for s in services:
        services_dict[s] = dict()
        methods = pb.DESCRIPTOR.services_by_name[s].methods_by_name.keys()
        for m in methods:
            obj = pb.DESCRIPTOR.services_by_name[s].methods_by_name[m]
            # Inputs
            input_message = obj.input_type
            input_fields = input_message.fields_by_name.keys()
            input_message_dict = dict()
            for f in input_fields:
                if input_message.fields_by_name[f].message_type:
                    input_message_dict[f] = {
                        "name": input_message.fields_by_name[f].message_type.name,
                        "label": input_message.fields_by_name[f].label,
                        "type": input_message.fields_by_name[f].type
                    }
                    input_message_dict[f]["fields"] = get_nested_messages(input_message.fields_by_name[f].message_type)
                else:
                    input_message_dict[f] = {
                        "label": input_message.fields_by_name[f].label,
                        "type": input_message.fields_by_name[f].type
                    }
            # Outputs
            output_message = obj.output_type
            output_fields = output_message.fields_by_name.keys()
            output_message_dict = dict()
            for f in output_fields:
                if output_message.fields_by_name[f].message_type:
                    output_message_dict[f] = {
                        "name": output_message.fields_by_name[f].message_type.name,
                        "label": output_message.fields_by_name[f].label,
                        "type": output_message.fields_by_name[f].type
                    }
                    output_message_dict[f]["fields"] = get_nested_messages(output_message.fields_by_name[f].message_type)
                else:
                    output_message_dict[f] = {
                        "label": output_message.fields_by_name[f].label,
                        "type": output_message.fields_by_name[f].type
                    }
            services_dict[s][m] = {
                "input": {
                    "name": obj.input_type.name,
                    "fields": input_message_dict
                },
                "output": {
                    "name": obj.output_type.name,
                    "fields": output_message_dict
                },
            }
    return services_dict


def message_factory2(req, ret, parent=""):
    for k, v in req.items():
        if isinstance(v, dict):
            ret = message_factory2(v, ret, "{}.{}".format(parent, k))
        else:
            ret.append("{}.{}.{}".format(parent, k, str(v)))
    return ret


def message_factory(req, input_message, classes):
    if "fields" in input_message:
        nested_dict = input_message["fields"]
    else:
        nested_dict = input_message
    ret = dict()
    for f in req.keys():
        ret[f] = dict()
        var_type = nested_dict[f]['type']
        if var_type == FD.TYPE_MESSAGE:
            ret[f]["class"] = classes[nested_dict[f]['name']]
            ret[f]["params"] = message_factory(req[f][nested_dict[f]['name']], nested_dict[f]['fields'], classes)
        else:
            tmp_var = req.get(f, None)
            ret[f] = type_converter(tmp_var, var_type) if tmp_var else None
    return ret


def get_classes(module, classes):
    for sub_module in dir(module):
        c = getattr(module, sub_module)
        if getattr(c, 'DESCRIPTOR', None):
            if not getattr(c, 'sys', None):
                classes[c.__name__] = c
            else:
                get_classes(c, classes)
    return classes


app.run(debug=False,
        host=SERVER_HOST,
        port=SERVER_PORT,
        use_reloader=False,
        threaded=True,
        passthrough_errors=True)
