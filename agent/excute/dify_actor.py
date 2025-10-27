import requests
from thespian.actors import Actor
from agent.message import DifySchemaRequest, DifySchemaResponse, DifyExecuteRequest, DifyExecuteResponse,SubtaskErrorMessage
from config import CONNECTOR_RECORD_DB_URL
from connector.dify_connector import get_dify_registry, DifyRunRegistry


class DifyWorkflowActor(Actor):
    def __init__(self):
        super().__init__()
        # 不再需要预先初始化 api_key/base_url
        self.dify_api_key = None
        self.base_url = None

    def receiveMessage(self, message, sender):
        try:
            if isinstance(message, DifySchemaRequest):
                # 直接从请求中提取配置
                self.dify_api_key = message.api_key
                self.base_url = message.base_url.rstrip('/')

                schema = self._get_input_schema()
                self.send(sender, DifySchemaResponse(
                    task_id=message.task_id,
                    input_schema=schema,
                    echo_payload=message.echo_payload
                ))

            elif isinstance(message, DifyExecuteRequest):
                # 同理，假设 DifyExecuteRequest 也包含 api_key 和 base_url
                # 如果还没有，请同样改造它（见下方说明）
                self.dify_api_key = message.api_key
                self.base_url = message.base_url.rstrip('/')

                result = self._run_workflow(message.inputs, message.user)

                connector_record = get_dify_registry(CONNECTOR_RECORD_DB_URL)
                if not connector_record.register_run(result, message.task_id, sender):
                    self.send(sender, SubtaskErrorMessage(message.task_id, "DB register failed"))
                    return
                self.send(sender, DifyExecuteResponse(
                    task_id=message.task_id,
                    outputs=result["outputs"],
                    workflow_run_id=result["workflow_run_id"],
                    status=result["status"],
                    original_sender=message.original_sender
                ))

                

            else:
                # 可选：拒绝未知消息
                self.send(sender, {'error': f'Unsupported message type: {type(message)}'})

        except Exception as e:
            import traceback
            print(f"[DifyWorkflowActor ERROR] {e}")
            print(traceback.format_exc())

            # 根据消息类型返回对应错误响应
            if isinstance(message, DifySchemaRequest):
                self.send(sender, DifySchemaResponse(
                    task_id=message.task_id,
                    input_schema=[],
                    echo_payload=message.echo_payload,
                    error=str(e)
                ))
            elif isinstance(message, DifyExecuteRequest):
                self.send(sender, DifyExecuteResponse(
                    task_id=message.task_id,
                    outputs={},
                    workflow_run_id="",
                    status="failed",
                    original_sender=message.original_sender,
                    error=str(e)
                ))
            else:
                self.send(sender, {'error': str(e)})

    def _get_input_schema(self):
        headers = {
            "Authorization": f"Bearer {self.dify_api_key}",
            "Content-Type": "application/json"
        }
        url = f"{self.base_url}/parameters"
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            params_info = resp.json()
            print(f"[DifyWorkflowActor] Parameters schema: {params_info}")

            schema = []
            user_input_form = params_info.get("user_input_form", [])
            for item in user_input_form:
                for control_type, config in item.items():
                    if isinstance(config, dict) and "variable" in config:
                        schema.append({
                            "variable": config["variable"],
                            "label": config.get("label", config["variable"]),  # fallback to var name
                            "required": config.get("required", False)
                        })
            return schema

        except Exception as e:
            print(f"[ERROR] Failed to fetch Dify parameters schema: {e}")
            return []

    def _run_workflow(self, inputs: dict, user: str = "thespian_user"):
        headers = {
            "Authorization": f"Bearer {self.dify_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "inputs": inputs,
            "response_mode": "blocking",
            "user": user
        }
        url = f"{self.base_url}/workflows/run"
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        outputs = data.get('data', {}).get('outputs', {})
        return {
            "outputs": outputs,
            "workflow_run_id": data.get('workflow_run_id'),
            "status": data.get('data', {}).get('status')
        }