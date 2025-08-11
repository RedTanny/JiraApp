# Confluence MCP Server

A Model Context Protocol (MCP) server for Confluence integration using the FastMCP framework.

## 🚀 Features

- **Search Confluence Pages**: Search for pages using CQL (Confluence Query Language)
- **Get Page Details**: Retrieve detailed information about specific pages
- **List Spaces**: Get all available Confluence spaces
- **Content Type Search**: Search for specific content types (pages, blog posts, comments)

## 📋 Prerequisites

- Python 3.8+
- FastMCP framework
- atlassian package
- Confluence Cloud or Server instance
- Confluence API credentials

## 🔧 Installation

1. **Install dependencies:**
   ```bash
   pip install fastmcp atlassian
   ```

2. **Set environment variables:**
   ```bash
   export CONFLUENCE_URL="https://your-domain.atlassian.net"
   export CONFLUENCE_USERNAME="your-email@domain.com"
   export CONFLUENCE_API_TOKEN="your-api-token"
   ```

   Or create a `.env` file:
   ```bash
   cp confluence_config.env .env
   # Edit .env with your actual values
   ```

## 🏃‍♂️ Usage

### 1. Start the MCP Server

```bash
cd MCP/
python confluence_mcp_server.py
```

The server will start on port 8004 with SSE transport.

### 2. Register with LlamaStack

```bash
curl -X POST http://localhost:8321/v1/toolgroups \
  -H "Content-Type: application/json" \
  -d '{
    "toolgroup_id": "confluence_mcp_group",
    "provider_id": "model-context-protocol",
    "mcp_endpoint": {
      "uri": "http://localhost:8004/sse"
    }
  }'
```

### 3. Test the Server

```bash
python test_confluence_mcp.py
```

## 🛠️ Available Tools

### 1. `search_confluence_pages`
Search for Confluence pages using text queries.

**Parameters:**
- `query` (str): Search query string
- `space_key` (str, optional): Limit search to specific space
- `limit` (int): Maximum results (default: 10)

**Example:**
```
"Search for pages about API documentation"
```

### 2. `get_confluence_page`
Get detailed information about a specific page.

**Parameters:**
- `page_id` (str): Confluence page ID

**Example:**
```
"Get details for page ID 12345"
```

### 3. `get_confluence_spaces`
List all available Confluence spaces.

**Parameters:**
- None

**Example:**
```
"Show me all Confluence spaces"
```

### 4. `search_confluence_content`
Search for specific content types.

**Parameters:**
- `query` (str): Search query
- `space_key` (str, optional): Limit to space
- `content_type` (str): Type to search (page, blogpost, comment)
- `limit` (int): Maximum results (default: 10)

**Example:**
```
"Find blog posts about project updates"
```

## 🔍 Testing

### Environment Test
```bash
python test_confluence_mcp.py
```

This will test:
- Environment variable configuration
- Confluence API connection
- MCP server connectivity
- Available tools

### Manual Testing

1. **Test Confluence API:**
   ```bash
   curl -u "username:api-token" \
     "https://your-domain.atlassian.net/rest/api/space"
   ```

2. **Test MCP Server:**
   ```bash
   curl http://localhost:8004/sse
   ```

## 🏗️ Architecture

```
Confluence MCP Server (Port 8004)
├── FastMCP Framework
├── Confluence API Client
├── CQL Query Builder
└── Response Formatter
    ├── search_confluence_pages
    ├── get_confluence_page
    ├── get_confluence_spaces
    └── search_confluence_content
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CONFLUENCE_URL` | Confluence server URL | `https://your-domain.atlassian.net` |
| `CONFLUENCE_USERNAME` | Confluence username/email | `your-email@domain.com` |
| `CONFLUENCE_API_TOKEN` | Confluence API token | `your-api-token` |

### MCP Configuration

| Setting | Value |
|---------|-------|
| Port | 8004 |
| Transport | SSE |
| Framework | FastMCP |

## 🚨 Troubleshooting

### Common Issues

1. **Connection Failed:**
   - Check Confluence URL and credentials
   - Verify API token permissions
   - Test direct API connection

2. **Authentication Error:**
   - Ensure username is email address
   - Verify API token is correct
   - Check token permissions

3. **MCP Server Not Starting:**
   - Check port 8004 availability
   - Verify FastMCP installation
   - Check Python dependencies

### Debug Mode

Enable debug logging:
```python
logging.basicConfig(level=logging.DEBUG)
```

## 🔗 Integration

### With Generic Agent

The Confluence MCP can be used with the Generic Agent:

```python
from generic_agent import GenericAgent

agent = GenericAgent()
agent.register_mcp("confluence_mcp_group", "http://localhost:8004/sse")
agent.start()

# Now agent can handle Confluence queries
request_id = agent.submit_input("Search Confluence for API documentation")
```

### With LlamaStack

Register the MCP with LlamaStack to enable Confluence tools in AI conversations.

## 📝 License

This project follows the same license as the main MCP JIRA project. 