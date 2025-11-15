import sys
import os

# Add the 'new' directory to the path
new_path = r'e:\Data\Flora\new'
sys.path.insert(0, new_path)

from capabilities.optimization import MultiFeatureOptimizer

def test_multi_feature_optimizer():
    print("Testing MultiFeatureOptimizer...")
    
    # Initialize optimizer with some configuration
    config = {
        'default_parameters': {'param1': 1.0, 'param2': 0.5},
        'knowledge_base_path': None  # No storage for testing
    }
    
    optimizer = MultiFeatureOptimizer(config)
    print("✓ Optimizer initialized successfully")
    
    # Test optimize_task method with empty history
    parameters = optimizer.optimize_task({
        'task_name': 'test_task',
        'current_state': {'some_metric': 0.8},
        'constraints': {'param1': (0.0, 2.0), 'param2': (0.0, 1.0)}
    }, [])  # Pass empty history data
    print(f"✓ optimize_task returned parameters: {parameters}")
    
    # Test learn_from_result method with task_id and result
    optimizer.learn_from_result(
        task_id='test_task_id_1',
        result={'parameters': parameters, 'score': 0.9, 'context': {'task_name': 'test_task'}}
    )
    print("✓ learn_from_result completed")
    
    # Test get_best_parameters method
    best_params = optimizer.get_best_parameters()
    print(f"✓ get_best_parameters returned: {best_params}")
    
    # Test reset method
    optimizer.reset()
    print("✓ reset completed")
    
    # Test save_state and load_state methods
    state = optimizer.save_state()
    print(f"✓ save_state returned state with keys: {list(state.keys())}")
    
    optimizer.load_state(state)
    print("✓ load_state completed")
    
    # Test get_optimization_stats method
    stats = optimizer.get_optimization_stats()
    print(f"✓ get_optimization_stats returned: {stats}")
    
    print("\n🎉 All tests passed!")

if __name__ == "__main__":
    test_multi_feature_optimizer()