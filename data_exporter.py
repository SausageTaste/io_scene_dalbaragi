from typing import Dict


class ParseConfigs:
    def __init__(
        self,
        exclude_hidden_objects: bool = False,
    ):
        self.__exclude_hidden_objects = bool(exclude_hidden_objects)


def __parse_scene_v1(configs: ParseConfigs) -> Dict:
    return {
        "version": 1,
    }


def parse_scene(configs: ParseConfigs) -> Dict:
    return __parse_scene_v1(configs)
