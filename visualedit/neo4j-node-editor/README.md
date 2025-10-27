# Neo4j 双结构节点编辑器

一个基于Web的可视化节点编辑器，用于同时管理Neo4j图数据库中的层级树和同级网两种结构。

## 功能特点

- **双分屏可视化**：左侧展示层级树结构，右侧展示同级网结构
- **节点操作**：支持添加、删除、编辑节点及其属性
- **关系管理**：自动维护层级树的父子关系和同级网的双向连接
- **数据同步**：所有操作实时反映到Neo4j数据库，支持从数据库加载数据
- **批量操作**：支持批量更新节点属性
- **智能关系维护**：添加节点时自动在两种结构中创建对应关系

## 技术栈

- **前端**：HTML, CSS (Tailwind CSS), JavaScript (Cytoscape.js)
- **后端**：Python (FastAPI)
- **数据库**：Neo4j

## 环境要求

- Python 3.8+
- Node.js 14+ (用于前端开发)
- Neo4j 4.0+

## 安装与运行

### 1. 克隆项目

```bash
git clone https://github.com/yourusername/neo4j-node-editor.git
cd neo4j-node-editor
```

### 2. 配置Neo4j连接

编辑 `backend/.env` 文件，设置你的Neo4j连接信息：

```
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=yourpassword
```

### 3. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

### 4. 运行后端服务

```bash
cd backend
uvicorn app.main:app --reload
```

后端服务将在 `http://localhost:8000` 运行。

### 5. 运行前端

可以直接在浏览器中打开 `frontend/index.html` 文件，或者使用简单的HTTP服务器：

```bash
cd frontend
python -m http.server 8001
```

然后在浏览器中访问 `http://localhost:8001`。

## API文档

后端API文档可在 `http://localhost:8000/docs` 查看。

## 使用说明

### 添加节点

1. 点击"添加节点"按钮
2. 填写节点属性（名称、类型、层级等）
3. 点击"保存"按钮

新节点将自动添加到两种结构中，并根据层级自动建立父节点关系（如果有）和同级连接。

### 编辑节点

1. 双击要编辑的节点
2. 修改属性
3. 点击"保存"按钮

### 删除节点

1. 选择一个或多个节点
2. 点击"删除节点"按钮
3. 确认删除

### 设置父节点

1. 选择两个节点（第一个作为子节点，第二个作为父节点）
2. 点击"设置父节点"按钮

### 添加同级连接

1. 选择至少两个节点
2. 点击"添加同级连接"按钮

### 批量更新属性

1. 点击"批量更新属性"按钮
2. 输入属性键和值
3. 选择应用范围（所有节点、选中节点或特定层级）
4. 点击"应用"按钮

### 保存与加载

- 点击"保存"按钮将当前状态保存到Neo4j
- 点击"加载"按钮从Neo4j加载数据

## 数据模型

### 节点属性

- `id`: 唯一标识符
- `name`: 节点名称
- `type`: 节点类型
- `level`: 层级树中的层级
- `properties`: 其他自定义属性（JSON格式）

### 关系类型

- `PARENT_OF`: 表示层级树中的父子关系
- `CONNECTED_TO`: 表示同级网中的双向连接关系

## 许可证

MIT License
