"""任务规划器实现"""
from typing import Dict, Any, List, Optional, Tuple
import networkx as nx
from ..capability_base import CapabilityBase
import logging
import uuid


class TaskPlanner(CapabilityBase):
    """
    任务规划器
    负责将复杂任务分解为子任务序列
    从TaskCoordinator.plan_subtasks迁移而来
    """
    
    def __init__(self):
        """
        初始化任务规划器
        """
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.registry = None  # 将在initialize中设置
        self.graph = None
        self.change_engine = None
        self.task_templates = {
            # 预定义的任务模板
            'data_analysis': {
                'steps': [
                    {'name': '数据收集', 'task_type': 'data_collection'},
                    {'name': '数据清洗', 'task_type': 'data_cleaning'},
                    {'name': '数据分析', 'task_type': 'analysis'},
                    {'name': '结果生成', 'task_type': 'result_generation'}
                ]
            },
            'research': {
                'steps': [
                    {'name': '信息收集', 'task_type': 'information_gathering'},
                    {'name': '信息分析', 'task_type': 'analysis'},
                    {'name': '结论生成', 'task_type': 'conclusion'}
                ]
            }
        }
    
    def get_capability_type(self) -> str:
        """
        获取能力类型
        """
        return 'planning'
    
    def initialize(self, registry=None, graph=None, change_engine=None) -> bool:
        """
        初始化任务规划器
        
        Args:
            registry: Agent注册表，用于获取可用Agent信息
            graph: 图结构（可选）
            change_engine: 变更引擎（可选）
            
        Returns:
            bool: 是否初始化成功
        """
        if not super().initialize():
            return False
        
        self.registry = registry
        self.graph = graph
        self.change_engine = change_engine
        return True
    
    def plan_subtasks(self, parent_agent_id: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        从TaskCoordinator.plan_subtasks迁移
        根据任务上下文规划子任务
        
        Args:
            parent_agent_id: 父Agent ID
            context: 任务上下文
            
        Returns:
            List[Dict[str, Any]]: 子任务列表
        """
        try:
            # 1. 分析任务类型和复杂度
            task_type = context.get('task_type')
            complexity = context.get('complexity', 0.5)
            
            # 2. 根据任务类型和复杂度选择规划策略
            if self.change_engine and self.registry and 'main_intent' in context:
                # 使用变更引擎进行规划
                return self._plan_with_change_engine(parent_agent_id, context)
            elif complexity < 0.3:
                # 简单任务，可能不需要分解
                return self._plan_simple_task(parent_agent_id, context)
            elif task_type in self.task_templates:
                # 使用预定义模板
                return self._plan_using_template(parent_agent_id, context, task_type)
            else:
                # 复杂任务，需要动态分解
                return self._plan_complex_task(parent_agent_id, context)
                
        except Exception as e:
            self.logger.error(f"Error planning subtasks: {str(e)}", exc_info=True)
            # 返回一个失败的回退子任务
            return [{
                'task_id': str(uuid.uuid4()),
                'task_type': 'error_handling',
                'context': {'error': str(e), 'original_context': context},
                'priority': 'high',
                'parent_agent_id': parent_agent_id
            }]
    
    def _plan_simple_task(self, parent_agent_id: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        规划简单任务（可能不需要分解）
        
        Args:
            parent_agent_id: 父Agent ID
            context: 任务上下文
            
        Returns:
            List[Dict[str, Any]]: 子任务列表
        """
        # 检查是否有子Agent可以直接执行
        if self.registry:
            children = self.registry.get_children(parent_agent_id)
            if children and len(children) == 1:
                # 如果只有一个子Agent，直接转发任务
                return [{
                    'task_id': str(uuid.uuid4()),
                    'task_type': context.get('task_type', 'direct_forward'),
                    'context': context,
                    'priority': context.get('priority', 'medium'),
                    'target_agent': children[0],
                    'parent_agent_id': parent_agent_id
                }]
        
        # 否则，返回原始任务作为唯一的子任务
        return [{
            'task_id': str(uuid.uuid4()),
            'task_type': context.get('task_type', 'original'),
            'context': context,
            'priority': context.get('priority', 'medium'),
            'parent_agent_id': parent_agent_id
        }]
    
    def _plan_using_template(self, parent_agent_id: str, context: Dict[str, Any], task_type: str) -> List[Dict[str, Any]]:
        """
        使用预定义模板规划任务
        
        Args:
            parent_agent_id: 父Agent ID
            context: 任务上下文
            task_type: 任务类型
            
        Returns:
            List[Dict[str, Any]]: 子任务列表
        """
        template = self.task_templates.get(task_type)
        if not template:
            self.logger.warning(f"Template not found for task type: {task_type}")
            return self._plan_simple_task(parent_agent_id, context)
        
        subtasks = []
        # 创建任务链，每个子任务都依赖前一个任务的结果
        for i, step in enumerate(template['steps']):
            subtask_context = context.copy()
            
            # 设置子任务特定信息
            subtask_context['step_index'] = i
            subtask_context['total_steps'] = len(template['steps'])
            subtask_context['step_name'] = step['name']
            
            # 添加依赖信息
            if i > 0:
                # 依赖前一个任务的结果
                subtask_context['previous_task_id'] = subtasks[i-1]['task_id']
                subtask_context['depends_on'] = [subtasks[i-1]['task_id']]
            else:
                subtask_context['depends_on'] = []
            
            # 创建子任务
            subtask = {
                'task_id': str(uuid.uuid4()),
                'task_type': step['task_type'],
                'context': subtask_context,
                'priority': context.get('priority', 'medium'),
                'step': i,
                'step_name': step['name'],
                'parent_agent_id': parent_agent_id
            }
            
            subtasks.append(subtask)
        
        return subtasks
    
    def _plan_complex_task(self, parent_agent_id: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
     ...

    def _plan_with_change_engine(self, parent_agent_id: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        使用Neo4j间接影响传播 + IntelligentChangeEngine生成执行计划
        """
        import networkx as nx
        import asyncio

        root_code = parent_agent_id  # 假设传入的是code，如 "rules_system_create_active"

        # 可配置阈值（可从config或context读取）
        threshold = context.get("influence_threshold", 0.3)

        # 1. 构建影响子图（含间接影响，权重为乘积）使用Neo4j查询
        graph: nx.DiGraph = self._fetch_influenced_subgraph_from_neo4j(
            root_code=root_code,
            threshold=threshold,
            max_hops=5
        )

        if not graph.nodes:
            return [{"node_id": root_code, "intent_params": {}}]

        # 2. 主意图
        main_intent = context.get("main_intent", "执行任务")

        # 3. 调用决策引擎
        change_request = {
            "graph": graph,
            "main_node": root_code,
            "main_intent": main_intent
        }

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(self.change_engine.run(change_request))
        finally:
            loop.close()

        strategy = result["strategy"]
        execution_order = strategy["dag_structure"]["execution_order"]
        intent_propagation = strategy.get("intent_propagation", {})

        # 4. 构建返回计划
        plan = []
        for node_code in execution_order:
            intent_params = intent_propagation.get(node_code, {})
            if not isinstance(intent_params, dict):
                intent_params = {"derived_intent": str(intent_params)}
            plan.append({
                "node_id": node_code,  # 注意：这里node_id实际是code
                "intent_params": intent_params
            })

        return plan

    def _fetch_influenced_subgraph_from_neo4j(
        self,
        root_code: str,
        threshold: float = 0.3,
        max_hops: int = 5
    ) -> nx.DiGraph:
        """
        从Neo4j获取影响子图
        """
        import networkx as nx

        query = """
        MATCH (start:MarketingDemo2 {code: $rootCode})
        CALL apoc.path.expandConfig(start, {
            relationshipFilter: 'SAME_LEVEL_DEMO1>',
            minLevel: 1,
            maxLevel: $maxHops,
            uniqueness: 'NODE_GLOBAL'
        }) YIELD path
        WITH path,
            reduce(acc = 1.0, r IN relationships(path) | acc * coalesce(r.weight, 0.0)) AS totalStrength
        WHERE totalStrength >= $threshold
        WITH nodes(path)[-1] AS target, totalStrength, path
        ORDER BY totalStrength DESC
        WITH target, head(collect({strength: totalStrength, path: path})) AS best
        RETURN
            best.path AS bestPath,
            best.strength AS totalStrength
        """
        graph = nx.DiGraph()

        # 先加入根节点
        root_node = self.registry.get_node_by_code(root_code)  # 假设registry有此方法
        if not root_node:
            raise ValueError(f"Root node {root_code} not found")
        graph.add_node(root_code, **root_node["properties"])

        with self.registry.driver.session() as session:
            results = session.run(query,
                                rootCode=root_code,
                                threshold=threshold,
                                maxHops=max_hops)
            # 处理结果，构建图
            for record in results:
                path = record["bestPath"]
                total_strength = record["totalStrength"]
                
                # 遍历路径中的节点和关系
                prev_node = None
                for node in path.nodes:
                    node_code = node["code"]
                    node_properties = dict(node)
                    
                    if node_code not in graph:
                        graph.add_node(node_code, **node_properties)
                    
                    if prev_node:
                        graph.add_edge(prev_node, node_code, weight=total_strength)
                    
                    prev_node = node_code

        return graph

    def _plan_complex_task(self, parent_agent_id: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        规划复杂任务，动态分解为子任务
        
        Args:
            parent_agent_id: 父Agent ID
            context: 任务上下文
            
        Returns:
            List[Dict[str, Any]]: 子任务列表
        """
        subtasks = []
        
        # 1. 分析任务需求
        task_requirements = self._analyze_task_requirements(context)
        
        # 2. 生成任务依赖图
        dependency_graph = self._generate_dependency_graph(task_requirements)
        
        # 3. 拓扑排序以确定执行顺序
        execution_order = self._topological_sort(dependency_graph)
        
        # 4. 创建子任务
        for task_name in execution_order:
            task_info = task_requirements.get(task_name, {})
            subtask_context = context.copy()
            subtask_context['subtask_name'] = task_name
            subtask_context['subtask_requirements'] = task_info.get('requirements', {})
            
            # 设置依赖
            dependencies = [dep for dep, tasks in dependency_graph.items() if task_name in tasks]
            subtask_context['depends_on'] = dependencies
            
            subtask = {
                'task_id': str(uuid.uuid4()),
                'task_type': task_info.get('task_type', 'complex_subtask'),
                'context': subtask_context,
                'priority': task_info.get('priority', context.get('priority', 'medium')),
                'name': task_name,
                'parent_agent_id': parent_agent_id
            }
            
            # 记录任务ID以便依赖关系
            for dep in dependencies:
                if dep in subtasks_map:
                    subtask_context[f'_{dep}_result'] = f"${{task_result:{subtasks_map[dep]}}}"
            
            subtasks.append(subtask)
            subtasks_map[task_name] = subtask['task_id']
        
        return subtasks
    
    def _analyze_task_requirements(self, context: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        分析任务需求，提取子任务信息
        
        Args:
            context: 任务上下文
            
        Returns:
            Dict[str, Dict[str, Any]]: 任务需求映射
        """
        requirements = {}
        
        # 从上下文中提取关键需求
        task_type = context.get('task_type', 'general')
        
        # 基于任务类型分析需求
        if task_type == 'problem_solving':
            requirements = {
                'understand_problem': {
                    'task_type': 'understanding',
                    'requirements': {'input': 'problem_description'},
                    'priority': 'high'
                },
                'research_solutions': {
                    'task_type': 'research',
                    'requirements': {'input': 'problem_summary'},
                    'priority': 'high'
                },
                'evaluate_solutions': {
                    'task_type': 'evaluation',
                    'requirements': {'input': 'potential_solutions'},
                    'priority': 'medium'
                },
                'select_solution': {
                    'task_type': 'selection',
                    'requirements': {'input': 'evaluation_results'},
                    'priority': 'high'
                },
                'generate_implementation': {
                    'task_type': 'implementation',
                    'requirements': {'input': 'selected_solution'},
                    'priority': 'medium'
                }
            }
        elif task_type == 'information_retrieval':
            requirements = {
                'parse_query': {
                    'task_type': 'parsing',
                    'requirements': {'input': 'query'},
                    'priority': 'high'
                },
                'search_resources': {
                    'task_type': 'search',
                    'requirements': {'input': 'parsed_query'},
                    'priority': 'high'
                },
                'filter_results': {
                    'task_type': 'filtering',
                    'requirements': {'input': 'raw_results'},
                    'priority': 'medium'
                },
                'summarize_information': {
                    'task_type': 'summarization',
                    'requirements': {'input': 'filtered_results'},
                    'priority': 'high'
                }
            }
        else:
            # 通用任务分解
            requirements = {
                'analyze_task': {
                    'task_type': 'analysis',
                    'requirements': {'input': 'task_description'},
                    'priority': 'high'
                },
                'execute_core': {
                    'task_type': task_type,
                    'requirements': {'input': 'analysis_result'},
                    'priority': 'high'
                },
                'finalize_result': {
                    'task_type': 'finalization',
                    'requirements': {'input': 'core_result'},
                    'priority': 'medium'
                }
            }
        
        return requirements
    
    def _generate_dependency_graph(self, requirements: Dict[str, Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        生成任务依赖图
        
        Args:
            requirements: 任务需求映射
            
        Returns:
            Dict[str, List[str]]: 依赖图，格式为 {task: [依赖的任务列表]}
        """
        graph = {}
        
        # 为每个任务初始化依赖列表
        for task_name in requirements:
            graph[task_name] = []
        
        # 构建依赖关系
        task_names = list(requirements.keys())
        for i, task_name in enumerate(task_names):
            if i > 0:
                # 简单实现：后一个任务依赖前一个任务
                # 实际应用中可能需要更复杂的依赖分析
                graph[task_name].append(task_names[i-1])
        
        return graph
    
    def _topological_sort(self, graph: Dict[str, List[str]]) -> List[str]:
        """
        拓扑排序依赖图
        
        Args:
            graph: 依赖图
            
        Returns:
            List[str]: 拓扑排序后的任务列表
        """
        # 计算每个节点的入度
        in_degree = {}
        for node in graph:
            in_degree[node] = 0
        
        for node in graph:
            for neighbor in graph[node]:
                in_degree[neighbor] += 1
        
        # 收集入度为0的节点
        queue = [node for node in in_degree if in_degree[node] == 0]
        
        # 拓扑排序
        result = []
        while queue:
            current = queue.pop(0)
            result.append(current)
            
            # 更新邻居节点的入度
            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        return result
    
    def register_task_template(self, template_name: str, template: Dict[str, Any]) -> bool:
        """
        注册任务模板
        
        Args:
            template_name: 模板名称
            template: 模板定义，包含steps字段
            
        Returns:
            bool: 是否注册成功
        """
        if 'steps' not in template or not isinstance(template['steps'], list):
            self.logger.error(f"Template must have 'steps' list")
            return False
        
        self.task_templates[template_name] = template
        self.logger.info(f"Registered task template: {template_name}")
        return True
    
    def get_task_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有任务模板
        
        Returns:
            Dict[str, Dict[str, Any]]: 任务模板映射
        """
        return self.task_templates.copy()
