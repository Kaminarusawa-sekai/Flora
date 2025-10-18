# dify_workflow_actor.py
import requests
from thespian.actors import Actor, requireCapability

@requireCapability('DifyActor')
class DifyWorkflowActor(Actor):
    def __init__(self):
        super().__init__()
        self.dify_api_key = None
        self.base_url = None

    def receiveMessage(self, message, sender):
        if not isinstance(message, dict):
            self.send(sender, {'error': 'Message must be a dictionary'})
            return

        # 初始化
        if 'api_key' in message and 'base_url' in message:
            self.dify_api_key = message['api_key']
            self.base_url = message['base_url'].rstrip('/')
            self.send(sender, {'status': 'initialized'})
            return

        if not (self.dify_api_key and self.base_url):
            self.send(sender, {'error': 'Actor not initialized. Send api_key and base_url first.'})
            return

        # 获取 input schema（即 Workflow 中定义的变量）
        if message.get('action') == 'get_input_schema':
            try:
                schema = self._get_input_schema()
                self.send(sender, {'input_schema': schema})
            except Exception as e:
                self.send(sender, {'error': f'Failed to fetch input schema: {str(e)}'})
            return

        # 执行 Workflow：必须提供 inputs
        if 'inputs' in message:
            try:
                response = self._run_workflow(
                    inputs=message['inputs'],
                    user=message.get('user', 'thespian_user')
                )
                self.send(sender, {'response': response})
            except Exception as e:
                self.send(sender, {'error': f'Workflow run error: {str(e)}'})
            return

        self.send(sender, {
            'error': 'For Workflow, you must send {"inputs": {...}}. '
                     'Use action="get_input_schema" to see required inputs.'
        })

    def _get_input_schema(self):
        """获取 Workflow 定义的输入变量"""
        headers = {
            "Authorization": f"Bearer {self.dify_api_key}",
            "Content-Type": "application/json"
        }
        url = f"{self.base_url}/application"
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        app_info = resp.json()
        return app_info.get('variables', [])

    def _run_workflow(self, inputs: dict, user: str = "thespian_user"):
        """调用 Dify Workflow 执行接口"""
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

        # Workflow 响应结构示例：
        # {
        #   "task_id": "...",
        #   "workflow_run_id": "...",
        #   "data": {
        #     "id": "...",
        #     "workflow_id": "...",
        #     "status": "succeeded",
        #     "outputs": { ... }  <-- 我们关心的结果
        #   }
        # }
        outputs = data.get('data', {}).get('outputs', {})
        return {
            "outputs": outputs,
            "workflow_run_id": data.get('workflow_run_id'),
            "status": data.get('data', {}).get('status')
        }