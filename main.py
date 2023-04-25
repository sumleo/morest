import argparse
import glob
import shutil
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
parser.add_argument("--chatgpt", type=bool, default=False)
parser.add_argument("--output_dir", type=str, default="output")
parser.add_argument("--rl", type=bool, default=False)
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
        strict=False,
    )
    apis = wrap_methods_from_open_api_document(parser.specification)
    return apis


def main():
    apis = parsing(args.yaml_path)

    # build odg
    odg = OperationDependencyGraph(apis)
    odg.build()
    graph = odg.generate_graph()

    # init fuzzer
    config = FuzzerConfig()
    config.time_budget = args.time_budget
    config.warm_up_times = args.warm_up_times
    config.url = args.url
    config.enable_chatgpt = args.chatgpt
    config.output_dir = args.output_dir
    config.enable_reinforcement_learning = args.rl
    fuzzer = Fuzzer(odg, config)

    # setup fuzzer
    fuzzer.setup()

    # warm up
    fuzzer.warm_up()

    # start fuzzing
    fuzzer.fuzz()


def list_folder_extract_yaml_files(folder_path: str):
    yaml_file_absolute_path_list = glob.glob(folder_path + "/*.json") + glob.glob(
        folder_path + "/*.yaml"
    )
    count = 0
    error_count = 0
    for yaml_file_absolute_path in yaml_file_absolute_path_list:
        try:
            loguru.logger.info(f"parsing {yaml_file_absolute_path}")
            apis = parsing(yaml_file_absolute_path)
            count += len(apis)
            # copy valid doc to another folder
            shutil.copy(
                yaml_file_absolute_path,
                "./valid_doc/" + yaml_file_absolute_path.split("/")[-1],
            )
        except Exception as e:
            error_count += 1
            loguru.logger.error(f"error: {e}")
    loguru.logger.info(f"total apis: {count}")
    loguru.logger.info(f"error apis: {error_count}")


if __name__ == "__main__":
    # list_folder_extract_yaml_files("./refine_document_new")
    main()
