# SolaGuard MCP Server

**Bible-Anchored Theology — Sola Scriptura Enforced**

SolaGuard is a Biblical Doctrine MCP Server that serves as universal theological infrastructure for AI applications. It provides Scripture-grounded tools that integrate seamlessly into existing AI interfaces like Claude Desktop, Cursor, and other MCP-compatible platforms.

## 🎯 Mission

Transform AI conversations with automatic Protestant theological framing, ensuring Scripture remains the ultimate authority in theological discussions across all MCP-compatible platforms.

## ✨ Features

### Core Biblical Research Tools
- **Scripture Lookup**: Retrieve verses with theological context (`get_verse`)
- **Verse Context**: Get surrounding verses for better interpretation (`get_verse_context`)
- **Biblical Search**: Full-text search across Scripture with FTS5 (`search_scripture`)
- **Interlinear Data**: Word-by-word Greek/Hebrew alignment with Strong's numbers
- **Word Studies**: Strong's concordance with 14,197 entries (`get_strongs`)
- **Cross-References**: 317,516 traditional cross-references (`get_cross_references`)
- **Topical Search**: Nave's Topical Bible with 5,500+ topics (`search_by_topic`)
- **Book Information**: Comprehensive biblical book metadata (`get_book_info`)

### Data Infrastructure
- **Complete Bible Texts**: KJV, BSB, and multiple translations
- **Strong's Dictionary**: 14,197 Greek/Hebrew lexicon entries with definitions
- **Cross-References**: 317,516 traditional cross-references for thematic study
- **Nave's Topical Bible**: 5,500+ curated topics with 100,000+ verse references
- **Interlinear Support**: 790,829 words with Strong's numbers, transliteration, and pronunciation
- **Theological Context**: Automatic Protestant framing in all responses
- **Zero Friction**: No authentication, no API keys, completely free

## 🚀 Quick Start

### Local Development (Recommended for Testing)

Run SolaGuard locally via stdio for immediate testing:

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

### For Claude Desktop Users (Local)

Add SolaGuard to your Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "solaguard": {
      "command": "uv",
      "args": ["run", "python", "-m", "solaguard.server"],
      "cwd": "/path/to/solaguard-mcp"
    }
  }
}
```

Restart Claude Desktop and start asking theological questions:

```
You: "What does Scripture say about love in 1 Corinthians 13?"

Claude: [Automatically calls get_verse tool]
"Based on 1 Corinthians 13:4-7..."
```

### For Hosted Deployment (Coming Soon)

Once deployed, you'll be able to connect via URL:

```json
{
  "mcpServers": {
    "solaguard": {
      "url": "https://api.solaguard.com/mcp"
    }
  }
}
```

### For Other MCP Clients

SolaGuard works with any MCP-compatible application:
- **Cursor IDE**: Add to MCP configuration
- **Windsurf IDE**: Configure in settings
- **Zed Editor**: Add to MCP servers
- **Custom Applications**: Use stdio or HTTP transport

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

## 📖 API Reference

### Core Tools

#### `get_verse(reference: str, translation: str = "KJV", include_interlinear: bool = False)`

Retrieve specific Bible verses with theological context.

**Parameters:**
- `reference`: Biblical reference (e.g., "John 3:16", "Romans 8:28-30")
- `translation`: Translation code (KJV, BSB, WEB, etc.)
- `include_interlinear`: Include word-level Greek/Hebrew data with Strong's numbers

**Example:**
```python
result = await get_verse("John 3:16", include_interlinear=True)
# Returns verse with word-by-word Greek breakdown, transliteration, and Strong's numbers
```

#### `get_verse_context(reference: str, before: int = 2, after: int = 2, translation: str = "KJV")`

Get a verse with surrounding context for better interpretation.

**Parameters:**
- `reference`: Single verse reference (e.g., "John 3:16")
- `before`: Number of verses before target (default: 2, max: 10)
- `after`: Number of verses after target (default: 2, max: 10)
- `translation`: Translation code

**Example:**
```python
result = await get_verse_context("John 3:16", before=2, after=2)
# Returns John 3:14-18 with verse 16 marked as target
```

#### `search_scripture(query: str, translation: str = "KJV", limit: int = 10)`

Full-text search across biblical content with FTS5 search engine.

**Parameters:**
- `query`: Search terms (supports phrases with quotes, boolean operators)
- `translation`: Translation to search
- `limit`: Maximum results to return

**Example:**
```python
results = await search_scripture("love your enemies")
# Returns relevant verses with book metadata for AI analysis
```

#### `get_strongs(strongs_number: str, translation: str = "KJV", limit: int = 20)`

Perform Hebrew or Greek word study using Strong's Concordance numbers.

**Parameters:**
- `strongs_number`: Strong's number (e.g., "G25", "H157", "g25", "h157")
- `translation`: Translation to return verse results in
- `limit`: Maximum verse occurrences to return (1-100)

**Example:**
```python
result = await get_strongs("G25")  # Greek word "agape" (love)
# Returns definition, pronunciation, all occurrences, related words, usage statistics
```

#### `get_cross_references(reference: str, translation: str = "KJV", limit: int = 10)`

Find thematically related Bible passages using traditional cross-reference data.

**Parameters:**
- `reference`: Biblical reference (e.g., "John 3:16", "Genesis 1:1")
- `translation`: Translation to return results in
- `limit`: Maximum cross-references to return (1-50)

**Example:**
```python
result = await get_cross_references("John 3:16")
# Returns related passages with theological connections
```

#### `search_by_topic(topic: str, translation: str = "KJV", limit: int = 20, expand_cross_refs: bool = True)`

Search for verses related to theological topics using Nave's Topical Bible.

**Parameters:**
- `topic`: Topic or concept to search for (e.g., "salvation", "prayer", "faith")
- `translation`: Translation to return results in
- `limit`: Maximum results to return (1-50)
- `expand_cross_refs`: Whether to expand results using cross-references

**Example:**
```python
result = await search_by_topic("salvation")
# Returns curated verses organized by theological topics
```

#### `get_book_info(book_name: str, include_stats: bool = True)`

Retrieve comprehensive biblical book information and metadata.

**Parameters:**
- `book_name`: Book name (e.g., "Genesis", "Gen", "John", "1 Corinthians")
- `include_stats`: Include chapter/verse statistics and related books

**Example:**
```python
result = await get_book_info("Genesis")
# Returns author, genre, testament, chapter count, theological context
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
- **Complete Data**: 790,829 words with Strong's numbers, 317,516 cross-references, 5,500+ topics
- **Read-Only**: Immutable biblical data during runtime
- **Indexed**: Fast verse lookup and search performance

### MCP Protocol

- **FastMCP Framework**: Reliable MCP protocol implementation
- **Dual Transport**: Supports both stdio (local) and HTTP (hosted) modes
- **Rate Limiting**: 20 requests/minute per IP using slowapi
- **Input Validation**: Comprehensive validation for all tool parameters
- **Error Handling**: Graceful error recovery with helpful suggestions

### Current Status

**Production-Ready Features:**
- ✅ 8 fully functional MCP tools
- ✅ Complete biblical research infrastructure
- ✅ Rate limiting and input validation
- ✅ Protestant theological framing
- ✅ Real production data (no mock data)

**In Progress:**
- 🚧 Unit and integration tests
- 🚧 Docker containerization
- 🚧 Hosted deployment
- 🚧 Client setup documentation

## 🌍 Deployment

### Current Status: Local Development

SolaGuard currently runs in local development mode via stdio. Hosted deployment is planned.

### Running Locally

```bash
# Via stdio (for MCP clients)
uv run python -m solaguard.server

# Via HTTP (for testing)
uv run uvicorn solaguard.server:app --host 0.0.0.0 --port 8000
```

### Docker (Coming Soon)

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
4. Run tests: `uv run pytest` (tests coming soon)
5. Submit a pull request

### Guidelines

- **Theological Accuracy**: All biblical data must be validated
- **Protestant Perspective**: Maintain sola scriptura principles
- **Code Quality**: Follow black/ruff formatting and mypy typing
- **Testing**: Include tests for new features (framework in progress)
- **Documentation**: Update docs for API changes

### Current Development Priorities

1. **Testing Infrastructure**: Unit tests, property-based tests, integration tests
2. **Docker Containerization**: Package for hosted deployment
3. **Client Documentation**: Setup guides for Claude Desktop, Cursor, etc.
4. **Analytics** (Optional): Basic usage tracking for service improvement

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