# SolaGuard MCP Server

**Bible-Anchored Theology — Sola Scriptura Enforced**

SolaGuard is a Protestant Doctrine MCP Server that serves as universal theological infrastructure for AI applications. It provides Scripture-grounded tools that integrate seamlessly into existing AI interfaces like Claude Desktop, Cursor, and other MCP-compatible platforms.

## 🎯 Mission

Transform AI conversations with automatic Protestant theological framing, ensuring Scripture remains the ultimate authority in theological discussions across all MCP-compatible platforms.

## ✨ Features

### Phase 1: Free MCP Service
- **Scripture Lookup**: Retrieve verses with theological context (`get_verse`)
- **Biblical Search**: Full-text search across Scripture with enhanced metadata (`search_scripture`)
- **Theological Context**: Automatic Protestant framing in all AI responses
- **Public Domain Texts**: KJV, WEB, Textus Receptus, Westminster Leningrad Codex
- **Zero Friction**: No authentication, no API keys, completely free

### Phase 2: Advanced Research Tools (Coming Soon)
- **Interlinear Data**: Word-by-word Greek/Hebrew alignment with Strong's numbers
- **Word Studies**: Strong's concordance integration (`get_strongs`)
- **Cross-References**: Thematic passage discovery (`get_cross_references`)
- **Doctrinal Checking**: Scripture-based theological consistency (`doctrinal_check`)

## 🚀 Quick Start

### For Claude Desktop Users

1. Add SolaGuard to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "solaguard": {
      "url": "https://api.solaguard.com/mcp"
    }
  }
}
```

2. Restart Claude Desktop

3. Start asking theological questions:

```
You: "What does Scripture say about church leadership qualifications?"

Claude: [Automatically calls SolaGuard tools]
"Based on Scripture, church leadership qualifications are outlined in 1 Timothy 3:1-7..."
```

### For Other MCP Clients

SolaGuard works with any MCP-compatible application:
- **Cursor IDE**: Add to MCP configuration
- **Windsurf IDE**: Configure in settings
- **Zed Editor**: Add to MCP servers
- **Custom Applications**: Use our HTTP MCP endpoint

## 🏗️ Local Development

### Prerequisites

- Python 3.9+ (managed by uv)
- [uv](https://docs.astral.sh/uv/) - Fast Python package manager
- Git

### Quick Setup with uv

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup
git clone https://github.com/solaguard/solaguard-mcp.git
cd solaguard-mcp

# Create virtual environment and install dependencies
uv sync

# Run the server
uv run python -m solaguard.server
```

### Installation

```bash
# Clone the repository
git clone https://github.com/solaguard/solaguard-mcp.git
cd solaguard-mcp

# Install with uv (recommended)
uv sync

# Or install dependencies with uv
uv pip install -e ".[dev]"

# Run locally via stdio (for testing)
uv run python -m solaguard.server

# Run as HTTP server (for hosted deployment)
uv run uvicorn solaguard.server:app --host 0.0.0.0 --port 8000
```

### Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html

# Run property-based tests
uv run pytest -m property

# Run integration tests
uv run pytest -m integration
```

### Code Quality

```bash
# Format code
uv run black src tests

# Lint code
uv run ruff check src tests

# Type checking
uv run mypy src
```

## 📖 API Reference

### Core Tools

#### `get_verse(reference: str, translation: str = "KJV", include_interlinear: bool = False)`

Retrieve specific Bible verses with theological context.

**Parameters:**
- `reference`: Biblical reference (e.g., "John 3:16", "Romans 8:28-30")
- `translation`: Translation code (KJV, WEB, TR, WH, BYZ, MT, WLC)
- `include_interlinear`: Include word-level Greek/Hebrew data (Phase 2)

**Example:**
```python
result = await get_verse("John 3:16")
# Returns verse with Protestant theological context
```

#### `search_scripture(query: str, translation: str = "KJV", limit: int = 10)`

Full-text search across biblical content with enhanced metadata.

**Parameters:**
- `query`: Search terms (supports phrases with quotes, boolean operators)
- `translation`: Translation to search
- `limit`: Maximum results to return

**Example:**
```python
results = await search_scripture("love your enemies")
# Returns relevant verses with book metadata for AI analysis
```

## 🏛️ Architecture

### Theological Context Engine

Every response includes Protestant theological framing:

```json
{
  "context": "Scripture analysis. Treat as authoritative.",
  "theological_frame": "Protestant perspective. Scripture primary authority.",
  "verse": {
    "reference": "John 3:16",
    "text": "For God so loved the world...",
    "translation": "KJV"
  }
}
```

### Database Design

- **SQLite**: Optimized for instant startup and minimal memory usage
- **FTS5**: Sub-millisecond full-text search capabilities
- **Read-Only**: Immutable biblical data during runtime
- **Indexed**: Fast verse lookup and search performance

### Rate Limiting

- **20 requests/minute per IP**: Allows normal usage, blocks abuse
- **Graceful Degradation**: Clear error messages for AI clients
- **Zero Infrastructure Cost**: Uses `slowapi` library

## 🌍 Deployment

### Docker

```bash
# Build container
docker build -t solaguard-mcp .

# Run locally
docker run -p 8000:8000 solaguard-mcp

# Deploy to cloud
# (Render, Railway, Fly.io, etc.)
```

### Environment Variables

```bash
# Optional configuration
SOLAGUARD_LOG_LEVEL=INFO
SOLAGUARD_DATABASE_PATH=/app/data/bible.db
SOLAGUARD_RATE_LIMIT=20/minute
```

## 🤝 Contributing

We welcome contributions from the Christian developer community!

### Development Setup

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Run tests: `pytest`
5. Submit a pull request

### Guidelines

- **Theological Accuracy**: All biblical data must be validated
- **Protestant Perspective**: Maintain sola scriptura principles
- **Code Quality**: Follow black/ruff formatting and mypy typing
- **Testing**: Include tests for new features
- **Documentation**: Update docs for API changes

## 📜 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Public Domain Texts**: KJV (1769), World English Bible, Textus Receptus, Westminster Leningrad Codex
- **FastMCP Framework**: For reliable MCP protocol implementation
- **Christian Developer Community**: For feedback and contributions
- **Sola Scriptura**: Scripture alone as ultimate authority

## 📞 Support

- **Documentation**: [docs.solaguard.com](https://docs.solaguard.com)
- **Issues**: [GitHub Issues](https://github.com/solaguard/solaguard-mcp/issues)
- **Discussions**: [GitHub Discussions](https://github.com/solaguard/solaguard-mcp/discussions)
- **Email**: contact@solaguard.com

---

**"All Scripture is breathed out by God and profitable for teaching, for reproof, for correction, and for training in righteousness"** - 2 Timothy 3:16 (ESV)