from dotenv import load_dotenv
load_dotenv()
import uuid
from langfuse import Langfuse
from langfuse.langchain import CallbackHandler
from .config.config import Settings

class FuseConfig:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FuseConfig,cls).__new__(cls)
            cls._instance._init()
        return cls._instance
    
    def _init(self):
        if self._initialized:
            return
        self._settings = Settings(r"C:\Users\Cristopher Hdz\Desktop\ui-protocol\ui-protocol\protocol-ag-ui\agent\util\config\config.yaml")   
        """ VM host """
        Langfuse(
            public_key=self._settings.langfuse.SECRET_KUBER_KEY,
            secret_key=self._settings.langfuse.SECRET_KUBER_KEY,
            host=self._settings.langfuse.KUBER_HOST
        )
        self._langfuse_handler = CallbackHandler()
        self._initialized = True

    def get_handler(self):
        return self._langfuse_handler
    
    def generate_id(self)->str:
        return str(uuid.uuid4())