import os
import sys
from pathlib import Path
import argparse
import json

from server import TranscoderServer


PROJECT_DIR = Path(__file__).absolute().parent
sys.path.insert(0, "{}".format(PROJECT_DIR))
from utils.proto_tools import load_proto


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    # gRPC API
    parser.add_argument("--proto-dir",
                        type=str,
                        default=os.environ.get("TRANSCODER_PROTO_DIR", "./protos"),
                        help="Path to .proto file(s) directory.")
    parser.add_argument("--grpc-host",
                        type=str,
                        default=os.environ.get("TRANSCODER_GRPC_HOST", "localhost"),
                        help="Transcoder gRPC server host.")
    parser.add_argument("--grpc-port",
                        type=int,
                        default=os.environ.get("TRANSCODER_GRPC_PORT", 7003),
                        help="Transcoder gRPC server port.")
    # REST API
    parser.add_argument("--host",
                        type=str,
                        default=os.environ.get("TRANSCODER_HOST", "localhost"),
                        help="Transcoder server host.")
    parser.add_argument("--port",
                        type=int,
                        default=os.environ.get("TRANSCODER_PORT", 7000),
                        help="Transcoder server port.")
    parser.add_argument("--cors",
                        action='store_true',
                        default=os.environ.get("TRANSCODER_CORS", False),
                        help="Allow CORS (all domains!).")
    parser.add_argument("--check-input",
                        type=str,
                        default=os.environ.get("TRANSCODER_CHECK_INPUT", None),
                        help="Inputs to make a check call on gRPC server.")
    parser.add_argument("--cert",
                        type=str,
                        default=os.environ.get("TRANSCODER_CERT", ""),
                        help="Path to certificate file.")
    parser.add_argument("--certkey",
                        type=str,
                        default=os.environ.get("TRANSCODER_CERTKEY", ""),
                        help="Path to cert key.")
    args = parser.parse_args()

    ssl_context = None
    if os.path.exists(args.cert) and os.path.exists(args.certkey):
        ssl_context = (args.cert, args.certkey)

    _, _, services_dict, classes, stubs = load_proto(args.proto_dir)

    rest_server = TranscoderServer(host=args.host,
                                   port=args.port,
                                   ssl_context=ssl_context,
                                   services_dict=services_dict,
                                   classes=classes,
                                   stubs=stubs,
                                   grpc_host=args.grpc_host,
                                   grpc_port=args.grpc_port,
                                   check_input=args.check_input,
                                   use_cors=args.cors)

    print("\n===== Configurations =====")
    for k, v in vars(args).items():
        tabs = "\t"
        if len(k) < 8:
            tabs = "\t\t"
        print("{}{}{}".format(k, tabs, v))
    print("==========================\n")
    
    rest_server.serve()
