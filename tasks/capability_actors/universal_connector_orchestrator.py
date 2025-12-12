from thespian.actors import Actor
from ..common.messages.connector_messages import (InvokeConnectorRequest, PrepareConnectorRequest, ExecuteConnectorRequest, ConnectorError, ConnectorResult, ConnectorExecutionSuccess, ConnectorExecutionFailure)
from ..external.execution_connectors import connector_registry as CONNECTOR_REGISTRY

class UniversalConnectorOrchestrator(Actor):
    def receiveMessage(self, msg, sender):
        if isinstance(msg, InvokeConnectorRequest):
            connector_name = msg.connector_name
            operation_name = msg.operation_name
            inputs = msg.inputs
            params = msg.params
            reply_to = msg.reply_to
            
            # 获取连接器信息
            capabilities = CONNECTOR_REGISTRY.get_capabilities(connector_name)
            connector_class = CONNECTOR_REGISTRY.get_connector_class(connector_name)
            
            # 生成任务ID
            import uuid
            task_id = f"task_{uuid.uuid4()}"
            
            try:
                # 直接实例化连接器
                # 使用params中的配置
                config = params.get("config", params.get("base_url", ""))
                if isinstance(params, dict):
                    config_dict = params.copy()
                else:
                    config_dict = {}
                    if hasattr(params, "to_dict"):
                        config_dict = params.to_dict()
                    elif isinstance(params, str):
                        config_dict["base_url"] = params
                connector = connector_class(config_dict)
                
                # 初始化连接器 - 跳过健康检查以避免API key验证
                if not connector.initialize(skip_health_check=True):
                    raise Exception(f"Failed to initialize connector: {connector_name}")
                
                try:
                    if operation_name == "prepare" and "prepare" in capabilities:
                        # 调用准备方法
                        prepare_result = connector.prepare(inputs)
                        try:
                            self.send(reply_to, ConnectorExecutionSuccess(
                                connector_name=connector_name,
                                result=prepare_result,
                                metadata={}
                            ))
                        except Exception:
                            # Ignore if reply_to is not a valid actor address
                            pass
                    elif operation_name == "execute" and "execute" in capabilities:
                        # 调用执行方法
                        execute_result = connector.execute(inputs, params)
                          
                        # 发送执行结果
                        try:
                            self.send(reply_to, ConnectorExecutionSuccess(
                                connector_name=connector_name,
                                result=execute_result,
                                metadata={}
                            ))
                        except Exception:
                            # Ignore if reply_to is not a valid actor address
                            pass
                    else:
                        # 不支持的操作
                        raise Exception(f"Unsupported operation: {operation_name} for connector: {connector_name}")
                except Exception as e:
                    # 处理执行异常
                    try:
                        self.send(reply_to, ConnectorExecutionFailure(
                            connector_name=connector_name,
                            error=str(e),
                            error_code=None,
                            original_request=inputs
                        ))
                    except Exception:
                        # Ignore if reply_to is not a valid actor address
                        pass
                finally:
                    # 确保连接器被关闭
                    connector.close()
                
            except Exception as e:
                # 发送错误结果
                try:
                    self.send(reply_to, ConnectorExecutionFailure(
                        connector_name=connector_name,
                        error=str(e),
                        error_code=None,
                        original_request=inputs
                    ))
                except Exception:
                    # Ignore if reply_to is not a valid actor address
                    pass
            
            # 退出actor
