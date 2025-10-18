from thespian.actors import Actor, ActorAddress
from typing import List, Optional


# 消息定义
class RouteDataQuery:
    def __init__(self, context_path: List[str], requester: ActorAddress):
        self.context_path = context_path  # e.g., ["Sales", "East", "Q3"]
        self.requester = requester


class RegistryRequest:
    def __init__(self, op: str, path: List[str]):
        self.op = op      # "has_data", "is_leaf", "children"
        self.path = path


class RegistryResponse:
    def __init__(self, result):
        self.result = result


class DataSourceFound:
    def __init__(self, data_actor_addr: ActorAddress):
        self.data_actor_addr = data_actor_addr


class DataSourceNotFound:
    pass


class DataRoutingActor(Actor):
    def __init__(self):
        super().__init__()
        self.registry_addr = None
        self.pending_requests = {}  # req_id -> (original_msg, state)

    def receiveMessage(self, msg, sender):
        if isinstance(msg, RouteDataQuery):
            # 初始化：先获取 registry 地址（假设已知或通过 global name）
            if self.registry_addr is None:
                self.registry_addr = self.actorSystem.ask(
                    'RegistryActor',  # 假设通过 global name 注册
                    None,
                    2.0
                )
                if not self.registry_addr:
                    self.send(msg.requester, DataSourceNotFound())
                    return

            req_id = id(msg)
            self.pending_requests[req_id] = {
                'original': msg,
                'state': 'search_local',
                'current_path': msg.context_path.copy()
            }
            self._search_step(req_id)

        elif isinstance(msg, RegistryResponse):
            # 找到 pending 请求
            for req_id, state in self.pending_requests.items():
                if 'waiting_for' in state and state['waiting_for'] == sender:
                    del state['waiting_for']
                    self._handle_registry_response(req_id, msg.result)
                    break

    def _search_step(self, req_id):
        state = self.pending_requests[req_id]
        path = state['current_path']

        if state['state'] == 'search_local':
            # Step 1: 检查当前路径是否有数据源
            self._ask_registry(req_id, "has_data", path)
            state['waiting_for'] = self.registry_addr
            state['next_state_if_true'] = 'check_if_leaf'
            state['next_state_if_false'] = 'search_children'

        elif state['state'] == 'check_if_leaf':
            # 如果有数据源，检查是否是叶子（具体持有者）
            self._ask_registry(req_id, "is_leaf", path)
            state['waiting_for'] = self.registry_addr
            state['next_state_if_true'] = 'found_leaf'
            state['next_state_if_false'] = 'search_children'

        elif state['state'] == 'search_children':
            # 检查子节点（向下找）
            self._ask_registry(req_id, "children", path)
            state['waiting_for'] = self.registry_addr
            state['next_state_if_true'] = 'try_children'
            state['next_state_if_false'] = 'search_parent'

        elif state['state'] == 'try_children':
            # children 是 list，逐个尝试（简化：只试第一个匹配的）
            children = state.get('registry_result', [])
            if not children:
                state['state'] = 'search_parent'
                self._search_step(req_id)
                return
            # 构造子路径
            child_path = path + [children[0]]  # 简化：只试第一个子节点
            state['current_path'] = child_path
            state['state'] = 'search_local'
            self._search_step(req_id)

        elif state['state'] == 'search_parent':
            # 向上回溯
            if len(path) <= 1:
                # 已到根，找不到
                self._fail(req_id)
                return
            parent_path = path[:-1]
            state['current_path'] = parent_path
            state['state'] = 'search_local'
            self._search_step(req_id)

        elif state['state'] == 'found_leaf':
            # 找到叶子节点，返回对应 DataQueryActor
            leaf_path = state['current_path']
            # 假设 DataQueryActor 通过路径命名（或从 registry 获取地址）
            data_actor_addr = self._resolve_data_actor(leaf_path)
            if data_actor_addr:
                self.send(state['original'].requester, DataSourceFound(data_actor_addr))
            else:
                self._fail(req_id)
            del self.pending_requests[req_id]

    def _handle_registry_response(self, req_id, result):
        state = self.pending_requests[req_id]
        state['registry_result'] = result

        if isinstance(result, bool):
            next_state = state['next_state_if_true'] if result else state['next_state_if_false']
        elif isinstance(result, list):
            next_state = state['next_state_if_true']  # children 返回 list，视为“有子”
        else:
            next_state = 'search_parent'  # fallback

        state['state'] = next_state
        self._search_step(req_id)

    def _ask_registry(self, req_id, op, path):
        self.send(self.registry_addr, RegistryRequest(op, path))

    def _resolve_data_actor(self, path: List[str]) -> Optional[ActorAddress]:
        # 策略1：通过 global name 查找
        name = "DataQueryActor_" + "_".join(path)
        try:
            return self.actorSystem.ask(name, None, 1.0)
        except:
            return None

    def _fail(self, req_id):
        orig = self.pending_requests[req_id]['original']
        self.send(orig.requester, DataSourceNotFound())
        del self.pending_requests[req_id]