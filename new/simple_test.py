#!/usr/bin/env python3
"""
Simple test script to verify the task group aggregator implementation
"""
import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from thespian.actors import ActorSystem, ActorExitRequest
from capability_actors.task_group_aggregator_actor import TaskGroupAggregatorActor
from common.messages.task_messages import TaskGroupRequest, TaskSpec


def test_task_group_aggregator():
    """
    Test the task group aggregator
    """
    print("Creating actor system...")
    actor_system = ActorSystem()
    
    try:
        # Create task group aggregator
        print("Creating task group aggregator...")
        aggregator = actor_system.createActor(TaskGroupAggregatorActor)
        
        # Create test tasks
        print("Creating test tasks...")
        tasks = [
            TaskSpec(task_id="task1", type="dify", content="Test task 1", task_metadata={}),
            TaskSpec(task_id="task2", type="mcp", content="Test task 2", task_metadata={})
        ]
        
        # Create task group request
        print("Creating task group request...")
        group_request = TaskGroupRequest(
            source="test_source",
            destination=aggregator,
            group_id="group1",
            tasks=tasks,
            reply_to="test_reply"
        )
        
        # Send the request
        print("Sending task group request...")
        actor_system.tell(aggregator, group_request)
        
        print("Test completed successfully!")
        
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up
        print("Shutting down actor system...")
        actor_system.shutdown()


if __name__ == "__main__":
    test_task_group_aggregator()