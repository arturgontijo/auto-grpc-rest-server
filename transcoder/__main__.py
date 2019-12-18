import os
import sys
from pathlib import Path
import argparse

import grpc

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

    args = parser.parse_args()

    _, _, services_dict, classes, stubs = load_proto(args.proto_dir)

    rest_server = TranscoderServer(host=args.host,
                                   port=args.port,
                                   services_dict=services_dict,
                                   classes=classes,
                                   stubs=stubs,
                                   channel=grpc.insecure_channel("{}:{}".format(args.grpc_host, args.grpc_port)))

    print("\n===== Configurations =====")
    for k, v in vars(args).items():
        tabs = "\t"
        if len(k) < 5:
            tabs = "\t\t"
        print("{}{}{}".format(k, tabs, v))
    print("==========================\n")

    rest_server.serve()