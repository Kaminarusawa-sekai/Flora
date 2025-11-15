"""Vanna AI TextToSQL implementation"""
import asyncio
from typing import Optional, List, Dict, Any
import vanna
from ..text_to_sql import TextToSQL


class VannaTextToSQL(TextToSQL):
    """Vanna AI TextToSQL implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize VannaTextToSQL with configuration
        
        Args:
            config: Configuration dictionary including:
                - api_key: Vanna API key
                - model: Model name (e.g., "gpt-4", "gpt-3.5-turbo")
                - database_uri: Optional database connection URI
        """
        self.api_key = config.get("api_key")
        self.model = config.get("model", "gpt-3.5-turbo")
        self.database_uri = config.get("database_uri")
        
        # Initialize Vanna library
        vanna.set_api_key(self.api_key)
        vanna.set_model(self.model)
        
        # If database URI is provided, connect to the database
        if self.database_uri and "sqlite" in self.database_uri:
            vanna.connect_to_sqlite(self.database_uri)
    
    async def generate_sql(self, natural_language_query: str, **kwargs) -> str:
        """
        Generate SQL from natural language query using Vanna
        
        Args:
            natural_language_query: Natural language query string
            **kwargs: Additional parameters
            
        Returns:
            Generated SQL statement
        """
        # Use asyncio.to_thread to run synchronous Vanna method in async context
        sql = await asyncio.to_thread(
            vanna.generate_sql,
            question=natural_language_query,
            **kwargs
        )
        return sql
    
    async def execute_sql(self, sql: str, **kwargs) -> Dict[str, Any]:
        """
        Execute SQL query using Vanna
        
        Args:
            sql: SQL statement to execute
            **kwargs: Additional parameters
            
        Returns:
            Query result as a dictionary
        """
        # Use asyncio.to_thread to run synchronous Vanna method in async context
        result = await asyncio.to_thread(
            vanna.run_sql,
            sql=sql,
            **kwargs
        )
        return result
    
    async def get_table_info(self, table_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get table structure information
        
        Args:
            table_name: Optional table name to get info for
            
        Returns:
            Table structure information
        """
        # This method needs to be implemented based on Vanna's API
        # Currently, Vanna might not have a direct method for this
        # We'll implement a placeholder for now
        if table_name:
            return {table_name: "Table information not available through Vanna API directly"}
        else:
            return {"tables": "Table list not available through Vanna API directly"}
    
    async def add_training_data(self, query: str, sql: str) -> bool:
        """
        Add training data to Vanna
        
        Args:
            query: Natural language query
            sql: Corresponding SQL statement
            
        Returns:
            Whether training data was added successfully
        """
        try:
            # Use asyncio.to_thread to run synchronous Vanna method in async context
            await asyncio.to_thread(
                vanna.train,
                question=query,
                sql=sql
            )
            return True
        except Exception:
            return False
    
    async def get_training_data(self) -> List[Dict[str, Any]]:
        """
        Get all training data from Vanna
        
        Returns:
            List of training data
        """
        # Use asyncio.to_thread to run synchronous Vanna method in async context
        training_data = await asyncio.to_thread(vanna.get_training_data)
        return training_data