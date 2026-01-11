# SolaGuard MCP Server Tests

This directory contains all tests for the SolaGuard MCP Server, organized by test type and purpose.

## Test Structure

```
tests/
├── __init__.py                    # Test package initialization
├── conftest.py                    # Pytest configuration and fixtures
├── README.md                      # This file
│
├── test_reference_parser.py       # Unit tests for reference parsing
├── test_verse_retrieval.py        # Unit tests for verse retrieval
├── test_database_schema.py        # Unit tests for database schema
├── test_database_connection.py    # Unit tests for database connections
├── test_server.py                 # Unit tests for MCP server
│
├── integration/                   # Integration tests
│   ├── __init__.py
│   ├── test_full_integration.py   # Full system integration tests
│   └── test_mcp_protocol.py       # MCP protocol compliance tests
│
└── manual/                        # Manual/development tests
    ├── __init__.py
    └── test_quick_check.py         # Quick development test
```

## Running Tests

### Quick Test (Development)
```bash
python run_tests.py quick
```

### Unit Tests Only
```bash
python run_tests.py unit
# or just
python run_tests.py
```

### Integration Tests Only
```bash
python run_tests.py integration
```

### All Tests
```bash
python run_tests.py all
```

### Specific Test File
```bash
python run_tests.py test_reference_parser.py
python run_tests.py reference_parser  # shorthand
```

## Test Types

### Unit Tests (`tests/test_*.py`)
- **Fast execution** - No external dependencies
- **Isolated testing** - Mock database connections and external services
- **High coverage** - Test individual functions and classes
- **Automated** - Run on every commit/PR

**Files:**
- `test_reference_parser.py` - Biblical reference parsing logic
- `test_verse_retrieval.py` - Verse retrieval functionality (mocked)
- `test_database_schema.py` - Database schema creation and validation
- `test_database_connection.py` - Database connection management (mocked)
- `test_server.py` - MCP server functionality (mocked)

### Integration Tests (`tests/integration/`)
- **Real database** - Uses actual SQLite database with test data
- **Full system** - Tests complete workflows end-to-end
- **Slower execution** - Requires database initialization
- **Manual/CI** - Run before releases or manually during development

**Files:**
- `test_full_integration.py` - Complete system integration with real database
- `test_mcp_protocol.py` - MCP protocol compliance via JSON-RPC

### Manual Tests (`tests/manual/`)
- **Development aid** - Quick verification during development
- **Human readable** - Clear output for debugging
- **Flexible** - Easy to modify for specific testing needs

**Files:**
- `test_quick_check.py` - Quick verification that everything works

## Test Configuration

### Fixtures (`conftest.py`)
- `temp_db` - Temporary database with schema only
- `temp_db_with_verses` - Temporary database with sample verses
- `sample_verse_data` - Mock verse data for testing
- `sample_book_metadata` - Mock book metadata for testing

### Coverage
Unit tests generate coverage reports:
- Terminal output shows coverage percentages
- HTML report generated in `htmlcov/` directory

### Async Testing
All async tests use `pytest-asyncio` with `--asyncio-mode=auto`.

## Requirements

### Test Dependencies
```toml
[tool.uv.dev-dependencies]
pytest = ">=7.4.0"
pytest-asyncio = ">=0.21.0"
pytest-cov = ">=4.1.0"
```

### Database Requirements
- Integration tests require `data/bible_mock.db` to exist
- Run `python scripts/generate_mock_data.py` to create test database
- Unit tests use temporary databases created by fixtures

## Best Practices

### Writing Tests
1. **Unit tests** should be fast and isolated
2. **Mock external dependencies** in unit tests
3. **Use fixtures** for common test data
4. **Test both success and error cases**
5. **Use descriptive test names** that explain what is being tested

### Test Organization
1. **One test file per source file** when possible
2. **Group related tests** in test classes
3. **Use integration tests** for end-to-end workflows
4. **Keep manual tests simple** and human-readable

### Running Tests
1. **Run unit tests frequently** during development
2. **Run integration tests** before committing major changes
3. **Use quick test** for rapid feedback during development
4. **Check coverage** to ensure comprehensive testing

## Troubleshooting

### Common Issues

**"Database file not found"**
```bash
python scripts/generate_mock_data.py
```

**"pytest not found"**
```bash
uv sync --dev
```

**"Tests timeout"**
- Integration tests may timeout if server startup is slow
- Check that database exists and is accessible
- Verify all dependencies are installed

**"Import errors"**
- Ensure you're running tests from the project root
- Check that `src/` is in Python path (handled by conftest.py)
- Verify all dependencies are installed with `uv sync`