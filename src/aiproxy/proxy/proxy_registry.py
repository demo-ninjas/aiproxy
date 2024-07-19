from .abstract_proxy import AbstractProxy
from aiproxy.data import ChatConfig

class ProxyRegistry:
    _proxies:dict[str, AbstractProxy]
    _defaults:dict[type, AbstractProxy]

    def __init__(self):
        self._proxies = {}
        self._defaults = {}

    def add_proxy(self, name:str, proxy:AbstractProxy, make_default:bool = True):
        self._proxies[name] = proxy
        if make_default:
            self._defaults[type(proxy)] = proxy

    def get_proxy(self, name):
        return self._proxies.get(name, None)

    def get_default(self, proxy_type:type):
        return self._defaults.get(proxy_type, None)

    def remove_proxy(self, name):
        del self._proxies[name]

    def get_all_proxies(self):
        return self._proxies.values()
    
    def load_proxy(self, name_or_config:ChatConfig|str, proxy_type:type, **kwargs):
        proxy = None
        
        if name_or_config is not None and type(name_or_config) is str: 
            # First, try loading the proxy by name
            proxy = self.get_proxy(name_or_config)
            if proxy is None: 
                ## Check if the name is a config name and load the config if it is
                from aiproxy.data import ChatConfig
                config = ChatConfig.load(name_or_config, False)
                if config is not None: 
                    name_or_config = config

        if name_or_config is not None:
            proxy = self.get_proxy(name_or_config.name)
        if proxy is None:
            proxy = proxy_type(name_or_config, **kwargs)
            self.add_proxy(name_or_config.name if name_or_config is not None else str(proxy_type), proxy)

        if proxy is not None and type(proxy) is not proxy_type:
            raise Exception(f"Proxy loaded with name {name_or_config.name} is not of the correct type")

        return proxy

    def __getitem__(self, name_or_type:str|type) -> AbstractProxy:
        if type(name_or_type) == type:
            return self._defaults[name_or_type]
        return self._proxies[name_or_type]

    def __contains__(self, name_or_type:str|type):
        if type(name_or_type) == type:
            return name_or_type in self._defaults
        return name_or_type in self._proxies
    
GLOBAL_PROXIES_REGISTRY = ProxyRegistry()