from fastapi import FastAPI, HTTPException, Body, Depends
from fastapi.middleware.cors import CORSMiddleware
from neo4j import GraphDatabase, exceptions
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Neo4j 双结构节点编辑器 API", version="1.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development only, restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Default Neo4j connection settings
DEFAULT_NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
DEFAULT_NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
DEFAULT_NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
DEFAULT_NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

# Global Neo4j driver instance
driver = None

# Initialize default Neo4j driver
def init_default_driver():
    global driver
    try:
        driver = GraphDatabase.driver(DEFAULT_NEO4J_URI, auth=(DEFAULT_NEO4J_USER, DEFAULT_NEO4J_PASSWORD))
        with driver.session(database=DEFAULT_NEO4J_DATABASE) as session:
            session.run("MATCH (n) RETURN count(n) AS count")
        print("Successfully connected to Neo4j with default settings!")
    except exceptions.AuthError:
        print("Neo4j authentication failed. Check your credentials.")
        driver = None
    except exceptions.ServiceUnavailable:
        print("Neo4j service is unavailable. Check if Neo4j is running and the URI is correct.")
        driver = None
    except Exception as e:
        print(f"Failed to connect to Neo4j: {str(e)}")
        driver = None

# Call initialization
init_default_driver()

# Pydantic model for Neo4j connection settings
class Neo4jConnectionSettings(BaseModel):
    uri: str
    user: str
    password: str
    database: str

# Function to get Neo4j driver with specific settings
def get_neo4j_driver(settings: Optional[Neo4jConnectionSettings] = None):
    """Get a Neo4j driver instance, using either provided settings or default/global driver"""
    if settings:
        # Create a temporary driver for testing connection
        temp_driver = GraphDatabase.driver(settings.uri, auth=(settings.user, settings.password))
        try:
            with temp_driver.session(database=settings.database):
                yield temp_driver
        finally:
            temp_driver.close()
    else:
        # Use the global driver
        if not driver:
            raise HTTPException(status_code=503, detail="Neo4j connection not available")
        yield driver

# Pydantic models
class Node(BaseModel):
    id: str
    name: str
    type: str
    level: int
    properties: Optional[Dict[str, Any]] = {}

class Edge(BaseModel):
    id: str
    source: str
    target: str
    label: str
    properties: Optional[Dict[str, Any]] = {}

class ParentRequest(BaseModel):
    childId: str
    parentId: str

class ConnectionRequest(BaseModel):
    nodeIds: List[str]

class BatchUpdateRequest(BaseModel):
    nodeIds: List[str]
    key: str
    value: str

class BatchDeleteRequest(BaseModel):
    nodeIds: List[str]

class LevelUpdateRequest(BaseModel):
    level: int

class SaveDataRequest(BaseModel):
    nodes: List[Node]
    parentEdges: List[Edge]
    networkEdges: List[Edge]

# API routes
@app.get("/")
async def root():
    return {"message": "Welcome to Neo4j 双结构节点编辑器 API"}

@app.post("/api/test-connection")
async def test_neo4j_connection(settings: Neo4jConnectionSettings):
    """Test Neo4j connection with provided settings"""
    try:
        # Create a temporary driver to test connection
        temp_driver = GraphDatabase.driver(settings.uri, auth=(settings.user, settings.password))
        with temp_driver.session(database=settings.database) as session:
            # Simple query to test connection
            result = session.run("RETURN 1 AS connection_test")
            record = result.single()
            if record and record["connection_test"] == 1:
                return {"success": True, "message": "Successfully connected to Neo4j"}
            else:
                return {"success": False, "message": "Connected but query failed"}
    except Exception as e:
        return {"success": False, "message": f"Connection failed: {str(e)}"}
    finally:
        if 'temp_driver' in locals():
            temp_driver.close()

# Node operations
@app.get("/api/nodes", response_model=List[Node])
async def get_all_nodes():
    """Get all nodes from the database"""
    if not driver:
        raise HTTPException(status_code=503, detail="Neo4j connection not available")
    
    try:
        with driver.session(database=DEFAULT_NEO4J_DATABASE) as session:
            result = session.run("""
                MATCH (n)
                RETURN n.id AS id, n.name AS name, n.type AS type, n.level AS level, n.properties AS properties
            """)
            
            nodes = [
                Node(
                    id=record["id"],
                    name=record["name"],
                    type=record["type"],
                    level=record["level"],
                    properties=record["properties"] or {}
                )
                for record in result
            ]
            
            return nodes
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving nodes: {str(e)}")

@app.get("/api/nodes/{node_id}", response_model=Node)
async def get_node(node_id: str):
    """Get a specific node by ID"""
    if not driver:
        raise HTTPException(status_code=503, detail="Neo4j connection not available")
    
    try:
        with driver.session(database=DEFAULT_NEO4J_DATABASE) as session:
            result = session.run("""
                MATCH (n {id: $node_id})
                RETURN n.id AS id, n.name AS name, n.type AS type, n.level AS level, n.properties AS properties
            """, node_id=node_id)
            
            record = result.single()
            if not record:
                raise HTTPException(status_code=404, detail="Node not found")
            
            return Node(
                id=record["id"],
                name=record["name"],
                type=record["type"],
                level=record["level"],
                properties=record["properties"] or {}
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving node: {str(e)}")

@app.post("/api/nodes", response_model=Node)
async def create_node(node: Node):
    """Create a new node"""
    if not driver:
        raise HTTPException(status_code=503, detail="Neo4j connection not available")
    
    try:
        with driver.session(database=DEFAULT_NEO4J_DATABASE) as session:
            # Check if node with same ID already exists
            existing_node = session.run("MATCH (n {id: $id}) RETURN n", id=node.id).single()
            if existing_node:
                raise HTTPException(status_code=400, detail=f"Node with ID {node.id} already exists")
            
            # Create the node
            result = session.run("""
                CREATE (n:Node {
                    id: $id,
                    name: $name,
                    type: $type,
                    level: $level,
                    properties: $properties
                })
                RETURN n.id AS id, n.name AS name, n.type AS type, n.level AS level, n.properties AS properties
            """, 
            id=node.id,
            name=node.name,
            type=node.type,
            level=node.level,
            properties=node.properties)
            
            record = result.single()
            return Node(
                id=record["id"],
                name=record["name"],
                type=record["type"],
                level=record["level"],
                properties=record["properties"] or {}
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating node: {str(e)}")

@app.put("/api/nodes/{node_id}", response_model=Node)
async def update_node(node_id: str, node: Node):
    """Update an existing node"""
    if not driver:
        raise HTTPException(status_code=503, detail="Neo4j connection not available")
    
    try:
        with driver.session(database=DEFAULT_NEO4J_DATABASE) as session:
            # Check if node exists
            existing_node = session.run("MATCH (n {id: $id}) RETURN n", id=node_id).single()
            if not existing_node:
                raise HTTPException(status_code=404, detail="Node not found")
            
            # Update the node
            result = session.run("""
                MATCH (n {id: $id})
                SET n.name = $name,
                    n.type = $type,
                    n.level = $level,
                    n.properties = $properties
                RETURN n.id AS id, n.name AS name, n.type AS type, n.level AS level, n.properties AS properties
            """, 
            id=node_id,
            name=node.name,
            type=node.type,
            level=node.level,
            properties=node.properties)
            
            record = result.single()
            return Node(
                id=record["id"],
                name=record["name"],
                type=record["type"],
                level=record["level"],
                properties=record["properties"] or {}
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating node: {str(e)}")

@app.delete("/api/nodes/{node_id}")
async def delete_node(node_id: str):
    """Delete a node and all its relationships"""
    if not driver:
        raise HTTPException(status_code=503, detail="Neo4j connection not available")
    
    try:
        with driver.session(database=DEFAULT_NEO4J_DATABASE) as session:
            # Check if node exists
            existing_node = session.run("MATCH (n {id: $id}) RETURN n", id=node_id).single()
            if not existing_node:
                raise HTTPException(status_code=404, detail="Node not found")
            
            # Delete the node and all relationships
            session.run("""
                MATCH (n {id: $id})
                DETACH DELETE n
            """, id=node_id)
            
            return {"success": True, "message": f"Node {node_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting node: {str(e)}")

@app.post("/api/nodes/batch-delete")
async def batch_delete_nodes(request: BatchDeleteRequest):
    """Delete multiple nodes and their relationships"""
    if not driver:
        raise HTTPException(status_code=503, detail="Neo4j connection not available")
    
    try:
        with driver.session(database=DEFAULT_NEO4J_DATABASE) as session:
            # Delete nodes and their relationships
            session.run("""
                UNWIND $node_ids AS node_id
                MATCH (n {id: node_id})
                DETACH DELETE n
            """, node_ids=request.nodeIds)
            
            return {"success": True, "message": f"{len(request.nodeIds)} nodes deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error batch deleting nodes: {str(e)}")

@app.post("/api/nodes/batch-update")
async def batch_update_nodes(request: BatchUpdateRequest):
    """Batch update a property for multiple nodes"""
    if not driver:
        raise HTTPException(status_code=503, detail="Neo4j connection not available")
    
    try:
        with driver.session(database=DEFAULT_NEO4J_DATABASE) as session:
            # Update nodes
            session.run("""
                UNWIND $node_ids AS node_id
                MATCH (n {id: node_id})
                SET n.properties[$key] = $value
                RETURN n.id AS id
            """, 
            node_ids=request.nodeIds,
            key=request.key,
            value=request.value)
            
            return {"success": True, "message": f"{len(request.nodeIds)} nodes updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error batch updating nodes: {str(e)}")

@app.patch("/api/nodes/{node_id}/level")
async def update_node_level(node_id: str, request: LevelUpdateRequest):
    """Update the level of a node"""
    if not driver:
        raise HTTPException(status_code=503, detail="Neo4j connection not available")
    
    try:
        with driver.session(database=DEFAULT_NEO4J_DATABASE) as session:
            # Check if node exists
            existing_node = session.run("MATCH (n {id: $id}) RETURN n", id=node_id).single()
            if not existing_node:
                raise HTTPException(status_code=404, detail="Node not found")
            
            # Update the node level
            session.run("""
                MATCH (n {id: $id})
                SET n.level = $level
            """, 
            id=node_id,
            level=request.level)
            
            return {"success": True, "message": f"Node {node_id} level updated to {request.level}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating node level: {str(e)}")

# Tree operations
@app.get("/api/tree", response_model=Dict[str, Any])
async def get_tree_structure():
    """Get the entire tree structure"""
    if not driver:
        raise HTTPException(status_code=503, detail="Neo4j connection not available")
    
    try:
        with driver.session(database=DEFAULT_NEO4J_DATABASE) as session:
            # Get all nodes and parent relationships
            result = session.run("""
                MATCH (n)
                OPTIONAL MATCH (n)-[r:PARENT_OF]->(m)
                RETURN n.id AS node_id, n.name AS node_name, n.type AS node_type, n.level AS node_level, n.properties AS node_properties,
                       r.id AS edge_id, r.label AS edge_label, m.id AS target_id
            """)
            
            nodes = {}
            edges = []
            
            for record in result:
                node_id = record["node_id"]
                if node_id not in nodes:
                    nodes[node_id] = {
                        "id": node_id,
                        "name": record["node_name"],
                        "type": record["node_type"],
                        "level": record["node_level"],
                        "properties": record["node_properties"] or {},
                        "children": []
                    }
                
                if record["target_id"]:
                    edges.append({
                        "id": record["edge_id"],
                        "source": node_id,
                        "target": record["target_id"],
                        "label": record["edge_label"]
                    })
                    
                    if record["target_id"] not in nodes:
                        # This should not happen if all nodes are returned
                        target_node = session.run("""
                            MATCH (m {id: $target_id})
                            RETURN m.id AS id, m.name AS name, m.type AS type, m.level AS level, m.properties AS properties
                        """, target_id=record["target_id"]).single()
                        
                        if target_node:
                            nodes[record["target_id"]] = {
                                "id": target_node["id"],
                                "name": target_node["name"],
                                "type": target_node["type"],
                                "level": target_node["level"],
                                "properties": target_node["properties"] or {},
                                "children": []
                            }
                
            # Build the tree hierarchy
            root_nodes = []
            for node_id, node_data in nodes.items():
                # Find parent
                parent_edge = next((e for e in edges if e["target"] == node_id), None)
                if parent_edge:
                    parent_id = parent_edge["source"]
                    if parent_id in nodes:
                        nodes[parent_id]["children"].append(node_data)
                else:
                    root_nodes.append(node_data)
            
            return {
                "root_nodes": root_nodes,
                "edges": edges
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving tree structure: {str(e)}")

@app.post("/api/tree/parent")
async def set_parent(request: ParentRequest):
    """Set parent for a node"""
    if not driver:
        raise HTTPException(status_code=503, detail="Neo4j connection not available")
    
    try:
        with driver.session(database=DEFAULT_NEO4J_DATABASE) as session:
            # Check if child and parent exist
            child_exists = session.run("MATCH (c {id: $child_id}) RETURN c", child_id=request.childId).single()
            parent_exists = session.run("MATCH (p {id: $parent_id}) RETURN p", parent_id=request.parentId).single()
            
            if not child_exists:
                raise HTTPException(status_code=404, detail=f"Child node {request.childId} not found")
            
            if not parent_exists:
                raise HTTPException(status_code=404, detail=f"Parent node {request.parentId} not found")
            
            # Remove existing parent relationships
            session.run("""
                MATCH (:Node)-[r:PARENT_OF]->(c {id: $child_id})
                DELETE r
            """, child_id=request.childId)
            
            # Create new parent relationship
            edge_id = f"parent-{request.parentId}-{request.childId}"
            session.run("""
                MATCH (p {id: $parent_id}), (c {id: $child_id})
                CREATE (p)-[r:PARENT_OF {id: $edge_id, label: 'PARENT_OF'}]->(c)
                RETURN r
            """, 
            parent_id=request.parentId,
            child_id=request.childId,
            edge_id=edge_id)
            
            return {"success": True, "message": f"Parent set for node {request.childId}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error setting parent: {str(e)}")

@app.delete("/api/tree/parent/{node_id}")
async def remove_parent(node_id: str):
    """Remove parent from a node"""
    if not driver:
        raise HTTPException(status_code=503, detail="Neo4j connection not available")
    
    try:
        with driver.session(database=DEFAULT_NEO4J_DATABASE) as session:
            # Check if node exists
            node_exists = session.run("MATCH (n {id: $node_id}) RETURN n", node_id=node_id).single()
            if not node_exists:
                raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
            
            # Remove parent relationship
            session.run("""
                MATCH (:Node)-[r:PARENT_OF]->(n {id: $node_id})
                DELETE r
            """, node_id=node_id)
            
            return {"success": True, "message": f"Parent removed from node {node_id}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error removing parent: {str(e)}")

# Network operations
@app.get("/api/network", response_model=Dict[str, Any])
async def get_network_structure():
    """Get the entire network structure"""
    if not driver:
        raise HTTPException(status_code=503, detail="Neo4j connection not available")
    
    try:
        with driver.session(database=DEFAULT_NEO4J_DATABASE) as session:
            # Get all nodes and network relationships
            nodes_result = session.run("""
                MATCH (n)
                RETURN n.id AS id, n.name AS name, n.type AS type, n.level AS level, n.properties AS properties
            """)
            
            edges_result = session.run("""
                MATCH (n)-[r:CONNECTED_TO]->(m)
                RETURN r.id AS id, r.label AS label, n.id AS source, m.id AS target, r.properties AS properties
            """)
            
            nodes = [
                {
                    "id": record["id"],
                    "name": record["name"],
                    "type": record["type"],
                    "level": record["level"],
                    "properties": record["properties"] or {}
                }
                for record in nodes_result
            ]
            
            edges = [
                {
                    "id": record["id"],
                    "source": record["source"],
                    "target": record["target"],
                    "label": record["label"],
                    "properties": record["properties"] or {}
                }
                for record in edges_result
            ]
            
            return {
                "nodes": nodes,
                "edges": edges
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving network structure: {str(e)}")

@app.post("/api/network/connect")
async def create_connections(request: ConnectionRequest):
    """Create connections between nodes"""
    if not driver:
        raise HTTPException(status_code=503, detail="Neo4j connection not available")
    
    try:
        with driver.session(database=DEFAULT_NEO4J_DATABASE) as session:
            # Check if all nodes exist
            for node_id in request.nodeIds:
                node_exists = session.run("MATCH (n {id: $node_id}) RETURN n", node_id=node_id).single()
                if not node_exists:
                    raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
            
            # Create connections between all pairs
            created_edges = []
            for i in range(len(request.nodeIds)):
                for j in range(i + 1, len(request.nodeIds)):
                    source_id = request.nodeIds[i]
                    target_id = request.nodeIds[j]
                    
                    # Check if connection already exists
                    existing_edge = session.run("""
                        MATCH (n {id: $source_id})-[r:CONNECTED_TO]->(m {id: $target_id})
                        RETURN r
                    """, source_id=source_id, target_id=target_id).single()
                    
                    if not existing_edge:
                        # Create connection
                        edge_id = f"conn-{source_id}-{target_id}"
                        session.run("""
                            MATCH (n {id: $source_id}), (m {id: $target_id})
                            CREATE (n)-[r:CONNECTED_TO {id: $edge_id, label: 'CONNECTED_TO'}]->(m)
                            RETURN r
                        """, 
                        source_id=source_id,
                        target_id=target_id,
                        edge_id=edge_id)
                        
                        created_edges.append(edge_id)
            
            return {"success": True, "message": f"Created {len(created_edges)} connections", "edges": created_edges}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating connections: {str(e)}")

@app.post("/api/network/disconnect")
async def remove_connections(request: ConnectionRequest):
    """Remove connections between nodes"""
    if not driver:
        raise HTTPException(status_code=503, detail="Neo4j connection not available")
    
    try:
        with driver.session(database=DEFAULT_NEO4J_DATABASE) as session:
            # Remove connections between all pairs
            removed_edges = 0
            for i in range(len(request.nodeIds)):
                for j in range(i + 1, len(request.nodeIds)):
                    source_id = request.nodeIds[i]
                    target_id = request.nodeIds[j]
                    
                    # Remove connection in both directions
                    result = session.run("""
                        MATCH (n {id: $source_id})-[r:CONNECTED_TO]->(m {id: $target_id})
                        DELETE r
                        RETURN count(r) AS count
                    """, source_id=source_id, target_id=target_id)
                    
                    removed_edges += result.single()["count"]
                    
                    result = session.run("""
                        MATCH (n {id: $target_id})-[r:CONNECTED_TO]->(m {id: $source_id})
                        DELETE r
                        RETURN count(r) AS count
                    """, source_id=source_id, target_id=target_id)
                    
                    removed_edges += result.single()["count"]
            
            return {"success": True, "message": f"Removed {removed_edges} connections"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error removing connections: {str(e)}")

# Save and load operations
@app.post("/api/save")
async def save_data(request: SaveDataRequest):
    """Save the entire graph data"""
    if not driver:
        raise HTTPException(status_code=503, detail="Neo4j connection not available")
    
    try:
        with driver.session(database=DEFAULT_NEO4J_DATABASE) as session:
            # Start a transaction
            tx = session.begin_transaction()
            
            try:
                # Clear existing data
                tx.run("MATCH (n) DETACH DELETE n")
                
                # Create nodes
                for node in request.nodes:
                    tx.run("""
                        CREATE (n:Node {
                            id: $id,
                            name: $name,
                            type: $type,
                            level: $level,
                            properties: $properties
                        })
                    """, 
                    id=node.id,
                    name=node.name,
                    type=node.type,
                    level=node.level,
                    properties=node.properties)
                
                # Create parent edges
                for edge in request.parentEdges:
                    tx.run("""
                        MATCH (source {id: $source}), (target {id: $target})
                        CREATE (source)-[r:PARENT_OF {
                            id: $id,
                            label: $label,
                            properties: $properties
                        }]->(target)
                    """, 
                    source=edge.source,
                    target=edge.target,
                    id=edge.id,
                    label=edge.label,
                    properties=edge.properties)
                
                # Create network edges
                for edge in request.networkEdges:
                    tx.run("""
                        MATCH (source {id: $source}), (target {id: $target})
                        CREATE (source)-[r:CONNECTED_TO {
                            id: $id,
                            label: $label,
                            properties: $properties
                        }]->(target)
                    """, 
                    source=edge.source,
                    target=edge.target,
                    id=edge.id,
                    label=edge.label,
                    properties=edge.properties)
                
                # Commit the transaction
                tx.commit()
                
                return {"success": True, "message": "Data saved successfully"}
            
            except Exception as e:
                # Rollback the transaction if any error occurs
                tx.rollback()
                raise e
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving data: {str(e)}")

@app.get("/api/load")
async def load_data():
    """Load the entire graph data"""
    if not driver:
        raise HTTPException(status_code=503, detail="Neo4j connection not available")
    
    try:
        with driver.session(database=DEFAULT_NEO4J_DATABASE) as session:
            # Get all nodes
            nodes_result = session.run("""
                MATCH (n)
                RETURN n.id AS id, n.name AS name, n.type AS type, n.level AS level, n.properties AS properties
            """)
            
            nodes = [
                {
                    "id": record["id"],
                    "name": record["name"],
                    "type": record["type"],
                    "level": record["level"],
                    "properties": record["properties"] or {}
                }
                for record in nodes_result
            ]
            
            # Get parent edges
            parent_edges_result = session.run("""
                MATCH (source)-[r:PARENT_OF]->(target)
                RETURN r.id AS id, r.label AS label, source.id AS source, target.id AS target, r.properties AS properties
            """)
            
            parent_edges = [
                {
                    "id": record["id"],
                    "source": record["source"],
                    "target": record["target"],
                    "label": record["label"],
                    "properties": record["properties"] or {}
                }
                for record in parent_edges_result
            ]
            
            # Get network edges
            network_edges_result = session.run("""
                MATCH (source)-[r:CONNECTED_TO]->(target)
                RETURN r.id AS id, r.label AS label, source.id AS source, target.id AS target, r.properties AS properties
            """)
            
            network_edges = [
                {
                    "id": record["id"],
                    "source": record["source"],
                    "target": record["target"],
                    "label": record["label"],
                    "properties": record["properties"] or {}
                }
                for record in network_edges_result
            ]
            
            return {
                "success": True,
                "data": {
                    "nodes": nodes,
                    "parentEdges": parent_edges,
                    "networkEdges": network_edges
                }
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading data: {str(e)}")

# Close Neo4j driver when app shuts down
@app.on_event("shutdown")
def shutdown_event():
    driver.close()
    print("Neo4j driver closed")
