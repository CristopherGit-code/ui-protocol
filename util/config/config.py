from typing import Dict, Any
from envyaml import EnvYAML
from box import Box
import sys

class Settings:
    _instance = None # not start

    # First method to call _init and return the instance for each new object
    def __new__(cls, file_path: str|None = None):
        if cls._instance is None:
            if file_path is None:
                raise ValueError("File path is required")
            cls._instance = super(Settings, cls).__new__(cls)
            cls._instance._init(file_path)
        return cls._instance
    
    # Check if the yaml has already been initialized and return
    def _init(self, config_file_path):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._config: Dict[str, Any] = self._load_config(config_file_path)
        self._initialized = True

    # Exit if the file is not loaded
    def _load_config(self, config_path: str = "config.yaml") -> Dict[str, Any]:
        #Load from yaml file with env variables
        try:
            return Box(dict(EnvYAML(config_path)))
        except FileNotFoundError:
            print(f"Config file not found: {config_path}. Exiting.")
            sys.exit(2)

    def __getattr__(self, name):
        config = self.__dict__.get("_config", None)
        if config is not None:
            return getattr(config, name, None)
        raise AttributeError(f"'Settings' object has no attribute '{name}'")

    def __repr__(self):
        return repr(self.__dict__.get("_config", {}))

    def __dir__(self):
        config = self.__dict__.get("_config", None)
        return dir(config) if config else super().__dir__()