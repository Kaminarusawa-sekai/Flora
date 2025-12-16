from tasks.capabilities.excution.connect.dify_connector import DifyConnector

dify_connector = DifyConnector()
dify_connector.execute(
    {"input": "你好"},
    {
        "api_key": "app-y96fZH5kCbv6YEuQtMZangg0",
        "base_url": "http://121.36.203.36:81/v1",

    }
)
