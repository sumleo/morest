import argparse
import glob
from typing import List

import loguru
import prance

from algo.fuzzer import Fuzzer
from constant.fuzzer_config import FuzzerConfig
from model.api import API
from model.operation_dependency_graph import OperationDependencyGraph
from util.api_document_warpper import wrap_methods_from_open_api_document

yaml_path = "https://petstore3.swagger.io/api/v3/openapi.json"
parser = argparse.ArgumentParser()
parser.add_argument("--yaml_path", type=str, default=yaml_path)
parser.add_argument("--time_budget", type=float, default=600)
parser.add_argument("--warm_up_times", type=int, default=5)
parser.add_argument("--url", type=str, default="http://localhost:8080/api/v3")
args = parser.parse_args()

logger = loguru.logger
logger.add("log/{time}.log")


def default_reclimit_handler(limit, parsed_url, recursions=()):
    """Raise prance.util.url.ResolutionError."""
    return {
        "type": "object",
    }


def parsing(api_document_path: str) -> List[API]:
    parser = prance.ResolvingParser(
        api_document_path,
        backend="openapi-spec-validator",
        recursion_limit_handler=default_reclimit_handler,
    )
    apis = wrap_methods_from_open_api_document(parser.specification)
    return apis


def main():
    apis = parsing(args.yaml_path)

    # build odg
    odg = OperationDependencyGraph(apis)
    odg.build()

    # init fuzzer
    config = FuzzerConfig()
    config.time_budget = args.time_budget
    config.warm_up_times = args.warm_up_times
    config.url = args.url
    fuzzer = Fuzzer(odg, config)

    # setup fuzzer
    fuzzer.setup()

    # warm up
    fuzzer.warm_up()

    # start fuzzing
    fuzzer.fuzz()


def list_folder_extract_yaml_files(folder_path: str):
    yaml_file_absolute_path_list = glob.glob(folder_path + "/*.json")
    count = 0
    for yaml_file_absolute_path in yaml_file_absolute_path_list:
        loguru.logger.info(f"parsing {yaml_file_absolute_path}")
        parsing(yaml_file_absolute_path)
    logger.info(
        f"total {count} / {len(yaml_file_absolute_path_list)} yaml files are parsed successfully"
    )


if __name__ == "__main__":
    # list_folder_extract_yaml_files("./doc")
    main()
