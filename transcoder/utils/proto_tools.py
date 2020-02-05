import os
import sys
from pathlib import Path
import traceback

import pkg_resources
from grpc_tools.protoc import main as protoc

from google.protobuf.descriptor import FieldDescriptor as Fd
# from google.protobuf import json_format


def load_proto(dir_path):
    if not isinstance(dir_path, Path):
        dir_path = Path(dir_path)

    # Adding path to the PYTHON_PATH
    sys.path.insert(0, str(dir_path.absolute()))

    services_dict = dict()
    classes = dict()
    stubs = dict()

    proto_file_list = dir_path.glob("*.proto")
    for proto_file in proto_file_list:
        compile_proto(entry_path=dir_path, codegen_dir=dir_path, proto_file=proto_file)

    compiled_proto_list = dir_path.glob("*.py")
    pb_list = []
    pb_grpc_list = []
    for compiled_proto_file in compiled_proto_list:
        compiled_proto_file = str(compiled_proto_file.absolute())
        if compiled_proto_file.endswith("_pb2.py"):
            pb_package = compiled_proto_file.split("/")[-1].replace(".py", "")
            pb_list.append(__import__(pb_package))
        elif compiled_proto_file.endswith("_pb2_grpc.py"):
            pb_grpc_package = compiled_proto_file.split("/")[-1].replace(".py", "")
            pb_grpc_list.append(__import__(pb_grpc_package))

    for pb in pb_list:
        services_dict = {**services_dict, **get_services(pb)}
        classes = {**classes, **get_classes(pb, classes)}

    for pb_grpc in pb_grpc_list:
        stubs = {**stubs, **get_stubs(pb_grpc, stubs)}

    return pb_list, pb_grpc_list, services_dict, classes, stubs


def type_converter(value, conversion_type):
    conversion_func = {
        Fd.TYPE_DOUBLE: float,
        Fd.TYPE_FLOAT: float,
        Fd.TYPE_INT64: int,
        Fd.TYPE_UINT64: int,
        Fd.TYPE_INT32: int,
        Fd.TYPE_FIXED64: float,
        Fd.TYPE_FIXED32: float,
        Fd.TYPE_BOOL: bool,
        Fd.TYPE_STRING: str,
        Fd.TYPE_GROUP: str,
        # Fd.TYPE_MESSAGE
        Fd.TYPE_BYTES: lambda x: bytes(x, encoding="utf-8") if isinstance(x, str) else bytes(x),
        Fd.TYPE_UINT32: int,
        Fd.TYPE_ENUM: int,
        Fd.TYPE_SFIXED32: float,
        Fd.TYPE_SFIXED64: float,
        Fd.TYPE_SINT32: int,
        Fd.TYPE_SINT64: int,
    }
    try:
        value = conversion_func[conversion_type](value)
    except Exception as e:
        print(e)
    return value


def get_services(pb):
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
                    output_message_dict[f]["fields"] = get_nested_messages(
                        output_message.fields_by_name[f].message_type)
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


def input_factory(req, input_message, classes):
    if "fields" in input_message:
        nested_dict = input_message["fields"]
    else:
        nested_dict = input_message
    ret = dict()
    for f in req.keys():
        var_type = nested_dict[f]["type"]
        var_label = nested_dict[f]["label"]
        if var_label == Fd.LABEL_REPEATED and var_type == Fd.TYPE_MESSAGE:
            ret[f] = []
            for v in req[f]:
                ret[f].append(classes[nested_dict[f]["name"]](**input_factory(v, nested_dict[f]["fields"], classes)))
        elif var_label == Fd.LABEL_REPEATED:
            ret[f] = []
            for v in req[f]:
                ret[f].append(type_converter(v, var_type))
        elif var_type == Fd.TYPE_MESSAGE:
            ret[f] = classes[nested_dict[f]["name"]](**input_factory(req[f], nested_dict[f]["fields"], classes))
        else:
            tmp_var = req.get(f, None)
            ret[f] = type_converter(tmp_var, var_type) if tmp_var else None
    return ret


def output_factory(obj, output_message):
    if "fields" in output_message:
        nested_dict = output_message["fields"]
    else:
        nested_dict = output_message
    ret = dict()
    for f in nested_dict.keys():
        tmp_obj = getattr(obj, f, None)
        var_type = nested_dict[f]["type"]
        var_label = nested_dict[f]["label"]
        if var_label == Fd.LABEL_REPEATED and var_type == Fd.TYPE_MESSAGE:
            ret[f] = []
            for v in tmp_obj:
                ret[f].append(output_factory(v, nested_dict[f]["fields"]))
        elif var_label == Fd.LABEL_REPEATED:
            ret[f] = []
            for v in tmp_obj:
                ret[f].append(type_converter(v, var_type))
        elif var_type == Fd.TYPE_MESSAGE:
            ret[f] = output_factory(tmp_obj, nested_dict[f]["fields"])
        else:
            tmp_var = getattr(obj, f, None)
            ret[f] = type_converter(tmp_var, var_type) if tmp_var else None
    return ret


def get_classes(module, classes):
    for sub_module in vars(module):
        c = getattr(module, sub_module, None)
        if getattr(c, "DESCRIPTOR", None):
            if not getattr(c, "sys", None):
                classes[c.__name__] = c
            else:
                get_classes(c, classes)
    return classes


def get_stubs(module, stubs):
    for sub_module in vars(module):
        if sub_module.endswith("Stub"):
            service_name = sub_module.replace("Stub", "")
            stubs[service_name] = getattr(module, sub_module, None)
    return stubs


def compile_proto(entry_path, codegen_dir, proto_file=None):
    try:
        if not os.path.exists(str(codegen_dir)):
            os.makedirs(str(codegen_dir))
        proto_include = pkg_resources.resource_filename('grpc_tools', '_proto')

        compiler_args = [
            "-I{}".format(entry_path),
            "-I{}".format(proto_include)
        ]

        compiler_args.insert(0, "protoc")
        compiler_args.append("--python_out={}".format(codegen_dir))
        compiler_args.append("--grpc_python_out={}".format(codegen_dir))

        if proto_file:
            compiler_args.append(str(proto_file))
        else:
            compiler_args.extend([str(p) for p in entry_path.glob("**/*.proto")])

        if not protoc(compiler_args):
            return True
        else:
            return False
    except Exception as e:
        print("{}\n{}".format(e, traceback.print_exc()))
        return False
