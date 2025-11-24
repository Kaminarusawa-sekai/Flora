import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'new')))

from thespian.actors import ActorSystem
from new.agents.execution.execution_strategy import MapReduceExecutionStrategy

# Create a simple task function that sometimes fails
async def simple_task_func(task):
    import random
    task_id = task.get("task_id", "unknown")
    if random.random() < 0.3:  # 30% chance of failure
        return {
            "success": False,
            "error": f"Task {task_id} failed randomly",
            "task_id": task_id
        }
    else:
        return {
            "success": True,
            "result": {
                "data": f"Result from task {task_id}",
                "value": 42
            },
            "task_id": task_id
        }

# Create a simple reduce function
def simple_reduce_func(results):
    successful_results = [r for r in results if r.get("success", False)]
    return {
        "success_count": len(successful_results),
        "total_tasks": len(results),
        "results": [r["result"] for r in successful_results]
    }

async def main():
    # Initialize the MapReduce execution strategy
    map_reduce_strategy = MapReduceExecutionStrategy()
    map_reduce_strategy.reduce_func = simple_reduce_func
    
    # Create test tasks with unique task_ids
    test_tasks = [
        {"task_id": f"task_{i}", "data": f"Task data {i}"} for i in range(5)
    ]
    
    print(f"Testing MapReduceExecutionStrategy with {len(test_tasks)} tasks...")
    
    try:
        # Execute the tasks
        result = await map_reduce_strategy.execute(test_tasks, simple_task_func)
        
        print(f"\nExecution Result:")
        print(f"Success: {result['success']}")
        print(f"Strategy: {result['strategy']}")
        print(f"Total Tasks: {result['total_tasks']}")
        print(f"Tasks Executed: {result['tasks_executed']}")
        print(f"Map Success: {result['map_success']}")
        print(f"Completed Tasks: {len(result['completed_tasks'])}")
        print(f"Failed Tasks: {len(result['failed_tasks'])}")
        print(f"Aggregated Result: {result['aggregated_result']}")
        
        if result['failed_tasks']:
            print(f"\nFailed Task Details:")
            for task_id, error in result['failed_tasks'].items():
                print(f"  - {task_id}: {error}")
                
    except Exception as e:
        print(f"\nExecution failed with exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
