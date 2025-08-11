# MCP JIRA Integration

A Model Context Protocol (MCP) server for integrating with JIRA and other Atlassian tools.

## ⚠️ **Security Notice**

This repository contains placeholder values for sensitive configuration. **Never commit real API tokens or credentials to version control.**

## Setup

### 1. Environment Variables

Create a `.env` file in the root directory with your actual credentials:

**Option 1: Copy the template**
```bash
cp env.template .env
# Then edit .env with your actual values
```

**Option 2: Create manually**
Create a `.env` file in the root directory:

```bash
# JIRA Configuration
JIRA_SERVER=your_jira_server_url_here
JIRA_API_TOKEN=your_jira_api_token_here

# Confluence Configuration (if using)
CONFLUENCE_URL=your_confluence_url_here
CONFLUENCE_API_TOKEN=your_confluence_api_token_here

# LlamaStack Configuration (if using)
LLAMA_STACK_URL=http://localhost:8321
LLAMA_STACK_MODEL=llama3.2:1b
LLAMA_STACK_TEMPERATURE=0.1
LLAMA_STACK_TOP_P=0.7
LLAMA_STACK_SESSION_NAME=generic-agent-laptop
LLAMA_STACK_OUTPUT_TIMEOUT=15.0
```

### 2. Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd mcp_jira

# Install dependencies
pip install -r requirements.txt

# Set up environment variables (see step 1)
```

### 3. Usage

```bash
# Start the MCP server
python Source/main.py

# Or run specific components
python MCP/jira_mcp_server.py
```

## Configuration Files

- `Source/mcp_servers.example.yaml` - Example MCP server configuration
- `Source/JiraApp.yaml` - Main application configuration

## Features

- JIRA issue retrieval and management
- Confluence integration (optional)
- MCP protocol support
- Console-based user interface
- Generic agent architecture

## Security Best Practices

1. **Never commit `.env` files** - They're already in `.gitignore`
2. **Use environment variables** for all sensitive data
3. **Rotate API tokens regularly**
4. **Use least-privilege access** for API tokens
5. **Monitor log files** for sensitive information

## Troubleshooting

If you encounter authentication issues:
1. Verify your API tokens are valid
2. Check that environment variables are properly set
3. Ensure your tokens have the necessary permissions
4. Check the server URLs are accessible from your network

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Ensure no sensitive data is included
5. Submit a pull request

## License

[Add your license information here] 