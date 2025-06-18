# MySQL Database Assistant

A powerful AI-powered MySQL database assistant that allows you to interact with your MySQL database using natural language. This tool uses OpenAI's Agents SDK to provide an intelligent interface for database operations.

![MySQL Agent](/screenshots/init.png)

## Features

- 🤖 Natural language interface for database queries
- 🔒 Secure query execution (only SELECT, SHOW, and DESCRIBE operations allowed)
- 📊 Formatted table output with automatic column width adjustment
- 🔍 Comprehensive table information and schema exploration
- ⚡ Asynchronous database operations using aiomysql
- 🔐 Environment-based configuration

## Prerequisites

- Python 3.6+
- MySQL Server
- OpenAI API Key

## Installation

1. Clone the repository:
```bash
git clone https://github.com/thakurcoderz/MySQL-Agent.git
cd MySQL-Agent
```

2. Install required dependencies:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Create a `.env` file in the project root with the following variables:
```env
OPENAI_API_KEY=your_openai_api_key
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=your_mysql_user
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=your_database_name
```

## Usage

Run the script:
```bash
python mysql_mcp_agent.py
```

The assistant will connect to your MySQL database and provide an interactive prompt where you can ask questions about your data.

> **Tip:** Run with the `--query` flag to print every SQL query executed to the CLI for transparency and debugging:
> ```bash
> python mysql_mcp_agent.py --query
> ```

> **Note:** All SELECT queries are automatically limited to 20 results for efficiency, even if you do not specify a LIMIT clause.

### Example Questions

- "What tables are in the database?"
- "Show me the structure of the users table"
- "How many records are in each table?"
- "Show me the first 5 users"
- "What are the most recent orders?"
- "Find all products with price > 100"

## Safety Features

- Only SELECT, SHOW, and DESCRIBE queries are allowed
- **All SELECT queries are automatically limited to 20 results if no LIMIT is specified**
- Automatic query result limiting (20 rows by default)
- SQL injection protection
- Table name sanitization
- Connection pooling for efficient resource usage

## Available Tools

1. `execute_sql_query`: Execute SELECT queries
2. `describe_table`: Get table structure
3. `list_tables`: List all tables in the database
4. `get_table_info`: Get comprehensive table information

## Error Handling

The assistant includes robust error handling for:
- Database connection issues
- Invalid queries
- Missing configuration
- API errors

## Conversation History & Follow-up Questions

The MySQL Database Assistant now supports context-aware, multi-turn conversations. This means you can ask follow-up questions and the agent will remember the last several turns of your conversation, allowing for more natural and productive interactions.

- The assistant maintains a history of the last 10 user and assistant turns.
- Each new question is answered in the context of the previous conversation, so you can ask things like:
  - "Show me the structure of the users table."
  - "Now show me the first 5 rows from it."
  - "What about the orders table?"
- This enables seamless, context-rich database exploration.

No special configuration is needed—just ask your questions as you would in a real conversation!

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Disclaimer

This tool is designed for database exploration and querying. It enforces strict safety measures to prevent destructive operations. Always ensure you have proper backups of your database before using any database tools. 