#!/usr/bin/env python3
"""
MySQL Agent Script using OpenAI Agents SDK with Direct MySQL Connection
This version connects directly to MySQL without requiring an MCP server.
"""

import asyncio
import os
from typing import Any, Dict, List, Optional
import logging

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("python-dotenv not found. Install with: pip install python-dotenv")

# OpenAI Agents SDK imports
from agents import Agent, Runner, function_tool

# MySQL connection
try:
    import aiomysql
except ImportError:
    print("aiomysql not found. Install with: pip install aiomysql")
    exit(1)

# Global database connection pool
db_pool: Optional[aiomysql.Pool] = None
database_config: Dict[str, Any] = {}

async def setup_mysql_connection(mysql_config: Dict[str, str]) -> bool:
    """Setup direct MySQL connection pool"""
    global db_pool, database_config
    
    try:
        database_config = mysql_config
        
        # Create connection pool
        db_pool = await aiomysql.create_pool(
            host=mysql_config["host"],
            port=int(mysql_config["port"]),
            user=mysql_config["user"],
            password=mysql_config["password"],
            db=mysql_config["database"],
            charset='utf8mb4',
            autocommit=True,
            maxsize=10,
            minsize=1,
        )
        
        # Test the connection
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT 1")
                result = await cursor.fetchone()
                if result[0] == 1:
                    print(f"✅ Connected to MySQL database: {mysql_config['database']}")
                    return True
        
        return False
        
    except Exception as e:
        print(f"❌ Failed to connect to MySQL: {e}")
        return False

async def execute_query(query: str) -> tuple[List[Dict[str, Any]], str]:
    """Execute a query and return results with status"""
    global db_pool
    
    if not db_pool:
        return [], "❌ No database connection available"
    
    try:
        async with db_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                # print(f"Executing query: {query}")
                await cursor.execute(query)
                
                # Handle different query types
                if query.strip().upper().startswith(('SELECT', 'SHOW', 'DESCRIBE', 'DESC')):
                    results = await cursor.fetchall()
                    return list(results), "✅ Query executed successfully"
                else:
                    # For INSERT, UPDATE, DELETE, etc.
                    affected_rows = cursor.rowcount
                    return [], f"✅ Query executed successfully. {affected_rows} rows affected."
                    
    except Exception as e:
        error_msg = f"❌ Error executing query: {str(e)}"
        print(error_msg)  # Log the error
        return [], error_msg

def format_query_results(results: List[Dict[str, Any]], status: str) -> str:
    """Format query results for display"""
    if not results:
        return status
    
    # Limit results for display
    display_results = results[:20]  # Show max 20 rows
    
    if len(display_results) == 0:
        return status
    
    # Get column headers
    headers = list(display_results[0].keys())
    
    # Calculate column widths
    col_widths = {}
    for header in headers:
        col_widths[header] = max(
            len(str(header)),
            max(len(str(row.get(header, ""))) for row in display_results)
        )
        # Limit column width for readability
        col_widths[header] = min(col_widths[header], 30)
    
    # Build formatted table
    formatted = status + "\n\n"
    
    # Header row
    header_row = " | ".join(str(header).ljust(col_widths[header]) for header in headers)
    formatted += header_row + "\n"
    formatted += "-" * len(header_row) + "\n"
    
    # Data rows
    for row in display_results:
        data_row = " | ".join(
            str(row.get(header, "")).ljust(col_widths[header])[:col_widths[header]] 
            for header in headers
        )
        formatted += data_row + "\n"
    
    # Add summary if there are more results
    if len(results) > len(display_results):
        formatted += f"\n... and {len(results) - len(display_results)} more rows\n"
    
    formatted += f"\nTotal rows: {len(results)}"

    # print(formatted)
    
    return formatted

@function_tool
async def execute_sql_query(query: str) -> str:
    """
    Execute a SQL query on the MySQL database.
    
    Args:
        query: The SQL query to execute (e.g., "SELECT * FROM users LIMIT 5")
    
    Returns:
        Query results formatted as a string
    """
    # Basic SQL injection protection - you might want to enhance this
    forbidden_keywords = ['DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE', 'INSERT', 'UPDATE']
    query_upper = query.upper().strip()
    
    for keyword in forbidden_keywords:
        if keyword in query_upper:
            return f"❌ Query contains forbidden keyword '{keyword}'. Only SELECT, SHOW, and DESCRIBE queries are allowed for safety."
    
    results, status = await execute_query(query)
    return format_query_results(results, status)

@function_tool
async def describe_table(table_name: str) -> str:
    """
    Get the structure/schema of a specific table, including column comments.
    
    Args:
        table_name: Name of the table to describe
    
    Returns:
        Table structure information with comments
    """
    # Sanitize table name to prevent SQL injection
    if not table_name.replace('_', '').replace('-', '').isalnum():
        return "❌ Invalid table name. Only alphanumeric characters, underscores, and hyphens are allowed."
    
    db_name = database_config.get('database', '')
    query = (
        "SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_KEY, COLUMN_DEFAULT, EXTRA, COLUMN_COMMENT "
        "FROM INFORMATION_SCHEMA.COLUMNS "
        f"WHERE TABLE_SCHEMA = '{db_name}' AND TABLE_NAME = '{table_name}'"
    )
    results, status = await execute_query(query)
    return format_query_results(results, status)

@function_tool
async def list_tables() -> str:
    """
    List all tables in the database.
    
    Returns:
        List of all tables in the database
    """
    query = "SHOW TABLES"
    results, status = await execute_query(query)
    return format_query_results(results, status)

@function_tool
async def get_table_info(table_name: str) -> str:
    """
    Get comprehensive information about a table including row count and basic stats.
    
    Args:
        table_name: Name of the table to analyze
    
    Returns:
        Table information including row count and column details
    """
    # Sanitize table name
    if not table_name.replace('_', '').replace('-', '').isalnum():
        return "❌ Invalid table name. Only alphanumeric characters, underscores, and hyphens are allowed."
    
    # Get table structure
    describe_results, describe_status = await execute_query(f"DESCRIBE `{table_name}`")
    
    # Get row count
    count_results, count_status = await execute_query(f"SELECT COUNT(*) as row_count FROM `{table_name}`")
    
    # Format response
    response = f"📊 Table Information: {table_name}\n\n"
    
    if count_results:
        row_count = count_results[0]['row_count']
        response += f"Total Rows: {row_count:,}\n\n"
    
    response += "Table Structure:\n"
    response += format_query_results(describe_results, describe_status)
    
    return response

def create_mysql_agent() -> Agent:
    """Create and configure the OpenAI agent with MySQL tools"""
    
    agent = Agent(
        name="MySQL Database Assistant",
        model="gpt-4.1-nano",
        instructions=f"""
        You are a helpful MySQL database assistant for the '{database_config.get('database', 'unknown')}' database.
            IMPORTANT SAFETY RULES:
            - You can only execute SELECT, SHOW, and DESCRIBE queries for safety
            - Always use LIMIT in SELECT queries to avoid overwhelming results (e.g., LIMIT 10)
            - Be careful with table and column names - they are case-sensitive in MySQL

            When users ask questions about data:
            1. Use list_tables() to see available tables if unsure about the database schema
            2. Use describe_table(table_name) or get_table_info(table_name) to understand table structure
            3. Use execute_sql_query(query) for custom SELECT queries to answer specific questions
            4. Always explain what you're doing and format results clearly
            5. If results are large, summarize key findings

            SQL Best Practices:
            - Use backticks around table/column names if they contain spaces or special characters
            - Use LIMIT to control result size (default to LIMIT 20 for large tables)
            - For text searches, use LIKE with wildcards (%)
            - Use proper WHERE clauses to filter data effectively
            - For dates, use proper MySQL date functions

            Example queries:
            - "SELECT * FROM users LIMIT 10"
            - "SELECT COUNT(*) FROM orders WHERE order_date >= '2024-01-01'"
            - "SHOW COLUMNS FROM products"

        Current database: {database_config.get('database', 'unknown')}
        Host: {database_config.get('host', 'unknown')}
        """,
        tools=[execute_sql_query, describe_table, list_tables, get_table_info]
    )
    
    return agent

async def cleanup():
    """Clean up database connections"""
    global db_pool
    if db_pool:
        db_pool.close()
        await db_pool.wait_closed()
        print("✅ Database connection closed")

async def main():
    """Main function to run the MySQL Agent"""
    
    # MySQL configuration from environment variables
    mysql_config = {
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "database": os.getenv("MYSQL_DATABASE", "test")
    }
    
    # Ensure OpenAI API key is set
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Please set OPENAI_API_KEY in your .env file")
        return
    
    # Validate MySQL config
    required_fields = ["host", "user", "database"]
    missing_fields = [field for field in required_fields if not mysql_config.get(field)]
    if missing_fields:
        print(f"❌ Missing required MySQL configuration: {', '.join(missing_fields)}")
        print("Please check your .env file")
        return
    
    try:
        print("🔧 Setting up MySQL connection...")
        if not await setup_mysql_connection(mysql_config):
            print("❌ Failed to setup MySQL connection. Exiting.")
            return
        
        print("🤖 Creating OpenAI agent...")
        agent = create_mysql_agent()
        
        print("✅ MySQL Agent ready!")
        print(f"Connected to database: {mysql_config['database']} at {mysql_config['host']}")
        print("\n🔒 Safety Note: Only SELECT, SHOW, and DESCRIBE queries are allowed")
        print("\nYou can now ask questions about your database!")
        print("\nExample questions:")
        print("- 'What tables are in the database?'")
        print("- 'Show me the structure of the users table'")
        print("- 'How many records are in each table?'")
        print("- 'Show me the first 5 users'")
        print("- 'What are the most recent orders?'")
        print("- 'Find all products with price > 100'")
        
        # Interactive loop
        while True:
            try:
                user_input = input("\n💬 Ask a question (or 'quit' to exit): ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    break
                
                if not user_input:
                    continue
                
                print("\n🤔 Thinking...")
                result = await Runner.run(agent, user_input)
                print(f"\n🤖 Response:\n{result.final_output}")
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    
    except Exception as e:
        print(f"❌ Failed to setup agent: {e}")
        print("Make sure your MySQL server is running and credentials are correct")
    
    finally:
        await cleanup()
        print("\n👋 Goodbye!")

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.WARNING)
    
    # Run the async main function
    asyncio.run(main())