from algo.fuzzer import Fuzzer


class RuntimeDictionary:
    """
    This class is used to store the runtime values of the parameters.
    """

    def __init__(self, fuzzer: Fuzzer):
        self.fuzzer: Fuzzer = fuzzer
