# Implementation Tasks: SolaGuard MCP Server

## Current Progress Summary

**Phase 1 Progress: 10/17 Core Tasks Completed (59%)**

### ✅ Completed Tasks:
- **Task Group 1**: Project Foundation (2/2 complete)
  - ✅ Task 1.1: Project Structure Setup
  - ✅ Task 1.2: FastMCP Server Foundation
- **Task Group 2**: Database Infrastructure (2/2 complete)
  - ✅ Task 2.1: Complete Database Schema Implementation
  - ✅ Task 2.2: Database Connection Management
- **Task Group 3**: Data Ingestion Pipeline (1/3 complete)
  - ✅ Task 3.1: Mock Data Generator for Development
- **Task Group 4**: Core MCP Tools (3/3 complete)
  - ✅ Task 4.1: Verse Retrieval Tool (`get_verse`)
  - ✅ Task 4.2: Scripture Search Tool (`search_scripture`)
  - ✅ Task 4.3: Theological Context Engine
- **Task Group 5**: Error Handling, Rate Limiting, and Validation (2/3 complete)
  - ✅ Task 5.1: Input Validation System
  - ✅ Task 5.2: Rate Limiting with slowapi

### 🚧 Next Priority Tasks:
- **Task 5.3**: Graceful Error Recovery (High Priority)
- **Task 6.1**: Unit Test Suite (High Priority)
- **Task 7.1**: Docker Containerization (High Priority)

### 🎯 Current Status:
**SolaGuard MCP Server is functional with core features complete:**
- ✅ Verse retrieval with theological context
- ✅ Full-text scripture search with FTS5
- ✅ Comprehensive input validation
- ✅ Rate limiting protection (20 req/min per IP)
- ✅ Protestant theological framing
- ✅ Mock data for development and testing

## Overview

This document breaks down the SolaGuard MCP Server implementation into specific, actionable development tasks based on the approved requirements and design documents. The implementation follows a two-phase approach: Phase 1 (free hosted MCP service) and Phase 2 (advanced theological research tools).

## Phase 1: Free MCP Service (MVP)

### Task Group 1: Project Foundation

#### Task 1.1: Project Structure Setup ✅
- [x] **COMPLETED**
**Priority:** Critical
**Estimated Effort:** 2 hours
**Dependencies:** None

**Acceptance Criteria:**
- [x] Create Python project with proper directory structure
- [x] Set up pyproject.toml with FastMCP, SQLite, and testing dependencies
- [x] Configure development environment with linting (black, ruff) and type checking (mypy)
- [x] Create basic README.md with project description and setup instructions
- [x] Initialize git repository with appropriate .gitignore for Python projects

**Implementation Notes:**
```
solaguard-mcp/
├── src/
│   └── solaguard/
│       ├── __init__.py
│       ├── server.py          # Main MCP server
│       ├── tools/             # MCP tool implementations
│       ├── database/          # Database operations
│       └── context/           # Theological context engine
├── data/                      # Source Bible texts
├── scripts/                   # Ingestion pipeline
├── tests/
├── pyproject.toml
└── README.md
```

#### Task 1.2: FastMCP Server Foundation ✅
- [x] **COMPLETED**
**Priority:** Critical
**Estimated Effort:** 4 hours
**Dependencies:** Task 1.1

**Acceptance Criteria:**
- [x] Implement basic FastMCP server with proper MCP protocol compliance
- [x] Configure server to support both stdio and HTTP transports
- [x] Add basic logging configuration for development and production
- [x] Implement health check endpoint for hosted deployment
- [x] Create server startup/shutdown lifecycle management

**Implementation Notes:**
- Use FastMCP framework for MCP protocol implementation
- Follow MCP specification for tool registration and response formats
- Ensure server can be run locally via stdio for development testing

### Task Group 2: Database Infrastructure

#### Task 2.1: Complete Database Schema Implementation ✅
- [x] **COMPLETED**
**Priority:** Critical
**Estimated Effort:** 6 hours
**Dependencies:** Task 1.1

**Acceptance Criteria:**
- [x] Create SQLite database schema matching design document specifications
- [x] Implement all tables: translations, books, verses, verses_fts
- [x] Create Phase 2 tables (empty): words, strongs_dictionary, cross_references
- [x] Create proper indexes for fast verse lookup and search performance
- [x] Set up FTS5 virtual table for full-text search capabilities
- [x] Add database migration system for future schema updates

**Implementation Notes:**
- Follow exact schema from design document
- Use SQLite FTS5 for search performance
- Include proper foreign key constraints and indexes
- Create Phase 2 tables now to prevent migration complexity later
- Tables can remain empty until Phase 2 data ingestion

#### Task 2.2: Database Connection Management ✅
- [x] **COMPLETED**
**Priority:** Critical
**Estimated Effort:** 3 hours
**Dependencies:** Task 2.1

**Acceptance Criteria:**
- [x] Implement database connection pool for concurrent read operations
- [x] Add connection retry logic with exponential backoff
- [x] Ensure read-only database access during runtime
- [x] Implement graceful error handling for database connection failures
- [x] Add database startup validation to ensure schema integrity

**Implementation Notes:**
- Use SQLite connection pooling for thread safety
- Implement connection health checks
- Never allow write operations during runtime (read-only requirement)

### Task Group 3: Data Ingestion Pipeline

### Task Group 3: Data Ingestion Pipeline (Phased Approach)

#### Task 3.1: Mock Data Generator for Development ✅
- [x] **COMPLETED**
**Priority:** Critical
**Estimated Effort:** 2 hours
**Dependencies:** Task 2.1

**Acceptance Criteria:**
- [x] Create mock data generator that produces valid database structure with sample verses
- [x] Generate representative sample data: 10-20 books, 50-100 verses, multiple translations
- [x] Include realistic biblical references (John 3:16, Genesis 1:1, Psalm 23:1, etc.)
- [x] Populate books table with proper metadata (testament, author, genre, canonical_order)
- [x] Create FTS5 search index with sample data for immediate testing
- [x] Enable immediate server.py development and MCP tool testing

**Implementation Notes:**
- Focus on creating valid database structure, not real biblical content
- Use well-known verses for testing (John 3:16, Romans 8:28, etc.)
- This unblocks all server development while real ingestion is built in parallel
- Sample data should be sufficient for comprehensive MCP tool testing

#### Task 3.2: Phase 1a - Plain Text Bible Processing (Real Data)
**Priority:** High
**Estimated Effort:** 4 hours
**Dependencies:** Task 3.1 (can be done in parallel)

**Acceptance Criteria:**
- [ ] Create ingestion scripts for plain text KJV (1769) and World English Bible (WEB)
- [ ] Process basic book/chapter/verse structure without Strong's numbers
- [ ] Generate optimized SQLite database with FTS5 search for production deployment
- [ ] Validate text integrity and completeness for core functionality
- [ ] Replace mock data with real biblical texts for production release

**Implementation Notes:**
- Focus on getting the service live quickly with basic functionality
- Use clean, well-formatted public domain texts (avoid parsing complexity)
- Implement core verse retrieval and search without interlinear data
- This enables production hosting and marketplace presence

#### Task 3.3: Phase 1b - Enhanced Text Processing (Strong's Integration)
**Priority:** Medium
**Estimated Effort:** 8 hours
**Dependencies:** Task 3.2, Phase 1a deployed and tested

**Acceptance Criteria:**
- [ ] Process KJV+ datasets with embedded Strong's tags for interlinear preparation
- [ ] Add Greek New Testament texts (Textus Receptus, Westcott-Hort, Byzantine)
- [ ] Add Hebrew Old Testament texts (Masoretic Text, Westminster Leningrad Codex)
- [ ] Create database migration system to upgrade from Phase 1a to 1b
- [ ] Maintain backward compatibility with existing MCP tool interfaces

**Implementation Notes:**
- This is the "data-cleaning nightmare" - tackle after service is proven
- Implement as database swap/migration rather than service downtime
- Prepare foundation for Phase 2 interlinear features
- Source from reliable repositories (Crosswire, OpenBible, OpenScriptures)

#### Task 3.2: Book Metadata Integration
**Priority:** High
**Estimated Effort:** 4 hours
**Dependencies:** Task 3.1

**Acceptance Criteria:**
- [ ] Populate books table with comprehensive metadata for all 66 canonical books
- [ ] Include testament classification (OT/NT), author attribution, and genre classification
- [ ] Set canonical ordering (1-66) for consistent book sequencing
- [ ] Add book abbreviation support for common formats (Gen, Jn, Rom, etc.)
- [ ] Validate book metadata completeness across all translations

**Implementation Notes:**
- Use standard Protestant canon (66 books)
- Include multiple abbreviation formats for user convenience
- Ensure metadata consistency across all supported translations

### Task Group 4: Core MCP Tools

#### Task 4.1: Verse Retrieval Tool (`get_verse`) ✅
- [x] **COMPLETED**
**Priority:** Critical
**Estimated Effort:** 6 hours
**Dependencies:** Task 2.2, Task 3.1

**Acceptance Criteria:**
- [x] Implement MCP tool with signature: `get_verse(reference: str, translation: str = "KJV", include_interlinear: bool = False)`
- [x] Parse biblical references in formats: "John 3:16", "Gen 1:1", "Romans 8:28-30"
- [x] Support abbreviated book names and multiple reference formats
- [x] Return structured verse data with theological context wrapper
- [x] Handle invalid references with clear error messages and format examples

**Implementation Notes:**
- Use regex patterns for flexible reference parsing
- Support both single verses and verse ranges
- Include theological context framework in all responses
- Prepare interlinear parameter for Phase 2 (return empty for now)

#### Task 4.2: Scripture Search Tool (`search_scripture`) ✅
- [x] **COMPLETED**
**Priority:** Critical
**Estimated Effort:** 8 hours
**Dependencies:** Task 2.2, Task 3.1

**Acceptance Criteria:**
- [x] Implement MCP tool with signature: `search_scripture(query: str, translation: str = "KJV", limit: int = 10)`
- [x] Use SQLite FTS5 for fast full-text search with BM25 ranking
- [x] Support phrase searches with quoted strings and boolean operators (AND, OR, NOT)
- [x] Return enhanced search results with book metadata for AI grouping
- [x] Include testament distribution and books found for comprehensive analysis

**Implementation Notes:**
- Leverage FTS5 for performance and relevance scoring
- Include comprehensive book metadata in response format
- Add context snippets for better AI understanding
- Implement proper query sanitization to prevent injection

#### Task 4.3: Theological Context Engine ✅
- [x] **COMPLETED**
**Priority:** High
**Estimated Effort:** 4 hours
**Dependencies:** Task 4.1, Task 4.2

**Acceptance Criteria:**
- [x] Implement context wrapper system for all MCP tool responses
- [x] Add Protestant theological framing to guide AI model responses
- [x] Create tool-specific context templates for different use cases
- [x] Ensure theological context is included but not visible to end users
- [x] Provide consistent biblical worldview framing across all tools

**Implementation Notes:**
- Follow exact context format from design document
- Create reusable context templates for different tool types
- Ensure context guides AI without being intrusive to users

### Task Group 5: Error Handling, Rate Limiting, and Validation

#### Task 5.1: Input Validation System ✅
- [x] **COMPLETED**
**Priority:** High
**Estimated Effort:** 4 hours
**Dependencies:** Task 4.1, Task 4.2

**Acceptance Criteria:**
- [x] Implement comprehensive input validation for all MCP tools
- [x] Validate biblical references against known book/chapter/verse ranges
- [x] Sanitize search queries to prevent malformed FTS5 queries
- [x] Return structured error responses with helpful suggestions
- [x] Ensure no crashes or exceptions reach the MCP client

**Implementation Notes:**
- Use consistent error response format across all tools
- Provide specific validation messages for different error types
- Include format examples in error responses

#### Task 5.2: Rate Limiting with slowapi ✅
- [x] **COMPLETED**
**Priority:** Critical
**Estimated Effort:** 3 hours
**Dependencies:** Task 5.1

**Acceptance Criteria:**
- [x] Install and configure slowapi library for FastAPI rate limiting
- [x] Access underlying FastAPI app from FastMCP framework (mcp._fastapi_app or equivalent)
- [x] Initialize slowapi limiter with app.state.limiter configuration
- [x] Implement "leaky bucket" rate limiting at 20 requests per minute per IP
- [x] Add rate limiting decorator to MCP message endpoint
- [x] Return HTTP 429 with user-friendly error messages when limits exceeded
- [x] Test rate limiting with normal usage (2-3 requests/minute) and abuse scenarios (50+ requests/second)

**Implementation Notes:**
```python
# FastMCP integration approach
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Access underlying FastAPI app from FastMCP
fastapi_app = mcp_server._fastapi_app  # or mcp.app depending on FastMCP version

# Initialize the limiter on FastAPI app
limiter = Limiter(key_func=get_remote_address)
fastapi_app.state.limiter = limiter
fastapi_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Apply to MCP endpoint
@fastapi_app.post("/mcp/messages")
@limiter.limit("20/minute")
async def handle_mcp_message(request: Request):
    return await mcp_server.process(request)
```

**User Experience:**
- Normal pastors: 2-3 verses/minute → No issues
- Abusive bots: 50+ requests/second → Blocked with clear error
- Claude receives: "Rate limit exceeded. Please try again in a few seconds."

#### Task 5.3: Graceful Error Recovery
**Priority:** High
**Estimated Effort:** 3 hours
**Dependencies:** Task 5.2

**Acceptance Criteria:**
- [ ] Handle database connection failures with retry logic
- [ ] Provide meaningful error messages for missing translations
- [ ] Implement fallback responses for temporary service issues
- [ ] Log errors appropriately without exposing sensitive information
- [ ] Maintain service availability during partial failures

**Implementation Notes:**
- Implement circuit breaker pattern for database operations
- Use structured logging for debugging and monitoring
- Never expose internal error details to MCP clients

### Task Group 6: Testing Infrastructure

#### Task 6.1: Unit Test Suite
**Priority:** High
**Estimated Effort:** 8 hours
**Dependencies:** Task 4.2, Task 5.1

**Acceptance Criteria:**
- [ ] Create comprehensive unit tests for all MCP tools
- [ ] Test biblical reference parsing with various formats
- [ ] Validate search functionality with different query types
- [ ] Test error handling for all known failure modes
- [ ] Achieve 90%+ code coverage for core functionality

**Implementation Notes:**
- Use pytest for test framework
- Create test fixtures with sample biblical data
- Mock database operations for isolated unit testing

#### Task 6.2: Property-Based Testing
**Priority:** Medium
**Estimated Effort:** 6 hours
**Dependencies:** Task 6.1

**Acceptance Criteria:**
- [ ] Implement property-based tests for all 12 correctness properties from design document
- [ ] Test with randomly generated biblical references and search queries
- [ ] Validate theological context consistency across all responses
- [ ] Run minimum 100 iterations per property test
- [ ] Tag tests with feature and property references

**Implementation Notes:**
- Use Hypothesis library for property-based testing
- Generate realistic biblical references for testing
- Validate universal properties across all valid inputs

### Task Group 7: Deployment and Documentation

#### Task 7.1: Docker Containerization
**Priority:** High
**Estimated Effort:** 4 hours
**Dependencies:** Task 6.1

**Acceptance Criteria:**
- [ ] Create Dockerfile for production deployment
- [ ] Optimize container size and startup time
- [ ] Include database file in container image
- [ ] Configure container for both local and hosted deployment
- [ ] Add health check endpoint for container orchestration

**Implementation Notes:**
- Use multi-stage build for smaller production image
- Ensure database is included and accessible in container
- Configure for deployment to Render, Railway, or similar platforms

#### Task 7.2: MCP Client Setup Documentation
**Priority:** High
**Estimated Effort:** 3 hours
**Dependencies:** Task 7.1

**Acceptance Criteria:**
- [ ] Create setup instructions for Claude Desktop integration
- [ ] Document configuration for other MCP-compatible clients
- [ ] Provide troubleshooting guide for common setup issues
- [ ] Include example conversations showing SolaGuard capabilities
- [ ] Create quick start guide for immediate usage

**Implementation Notes:**
- Focus on zero-friction setup experience
- Include JSON configuration examples for popular MCP clients
- Provide clear examples of theological conversations

## Phase 2: Advanced Theological Research Tools

### Task Group 8: Interlinear Data Infrastructure

#### Task 8.1: Strong's Dictionary Integration
**Priority:** Medium
**Estimated Effort:** 8 hours
**Dependencies:** Phase 1 Complete

**Acceptance Criteria:**
- [ ] Extend database schema with words and strongs_dictionary tables
- [ ] Process Strong's Concordance data (G1-G5624, H1-H8674)
- [ ] Create word-level alignment between original languages and English
- [ ] Implement lazy loading for interlinear data to maintain performance
- [ ] Validate Strong's number integrity across all biblical texts

**Implementation Notes:**
- Source Strong's data from public domain repositories
- Implement efficient word-level storage and retrieval
- Prepare for KJV+ dataset integration with embedded Strong's tags

#### Task 8.2: Original Language Text Processing
**Priority:** Medium
**Estimated Effort:** 10 hours
**Dependencies:** Task 8.1

**Acceptance Criteria:**
- [ ] Process Greek New Testament with morphological parsing
- [ ] Process Hebrew Old Testament with grammatical analysis
- [ ] Align original language words with Strong's numbers
- [ ] Include transliteration data for pronunciation guidance
- [ ] Validate morphological data completeness and accuracy

**Implementation Notes:**
- Use OpenScriptures morphology data or similar public domain sources
- Implement three-dataset merge strategy (KJV+, original texts, Strong's)
- Handle italicized words in KJV that have no original language equivalent

### Task Group 9: Advanced MCP Tools

#### Task 9.1: Strong's Word Study Tool (`get_strongs`)
**Priority:** Medium
**Estimated Effort:** 6 hours
**Dependencies:** Task 8.1

**Acceptance Criteria:**
- [ ] Implement MCP tool with signature: `get_strongs(strongs_number: str, limit: int = 20)`
- [ ] Return Strong's definition, pronunciation, and part of speech
- [ ] List all Scripture occurrences with context for word study
- [ ] Support both Hebrew (H1-H8674) and Greek (G1-G5624) numbers
- [ ] Include theological context for original language study

**Implementation Notes:**
- Validate Strong's number format and range
- Sort occurrences by canonical book order
- Include sufficient context for meaningful word study

#### Task 9.2: Cross-Reference Discovery Tool (`get_cross_references`)
**Priority:** Medium
**Estimated Effort:** 8 hours
**Dependencies:** Task 8.2

**Acceptance Criteria:**
- [ ] Implement MCP tool with signature: `get_cross_references(reference: str, limit: int = 10)`
- [ ] Find thematically related passages based on shared keywords and Strong's numbers
- [ ] Support curated cross-reference databases for common theological themes
- [ ] Return related verses with relevance scores and connection explanations
- [ ] Prioritize direct quotations, parallel passages, and conceptual connections

**Implementation Notes:**
- Implement algorithmic cross-reference discovery using Strong's numbers
- Create curated cross-reference database for major theological themes
- Use relevance scoring to rank cross-reference quality

#### Task 9.3: Doctrinal Consistency Tool (`doctrinal_check`)
**Priority:** Medium
**Estimated Effort:** 6 hours
**Dependencies:** Task 9.1

**Acceptance Criteria:**
- [ ] Implement MCP tool with signature: `doctrinal_check(topic: str)`
- [ ] Perform keyword-based search to find relevant Scripture passages
- [ ] Return raw Scripture verses for AI analysis rather than making doctrinal judgments
- [ ] Include hidden system instructions for Protestant theological framing
- [ ] Respond with "No clear biblical teaching found" when appropriate

**Implementation Notes:**
- Focus on Scripture presentation rather than doctrinal interpretation
- Include comprehensive theological context for AI guidance
- Maintain theological neutrality while providing Protestant framing

### Task Group 10: Enhanced Features

#### Task 10.1: Interlinear Data Integration
**Priority:** Medium
**Estimated Effort:** 6 hours
**Dependencies:** Task 8.2

**Acceptance Criteria:**
- [ ] Extend `get_verse` tool to support `include_interlinear=True` parameter
- [ ] Return word-by-word alignment with original language, transliteration, and Strong's numbers
- [ ] Include morphological parsing data (part of speech, tense, voice, mood, case, number)
- [ ] Handle missing morphological data gracefully
- [ ] Maintain performance by lazy-loading interlinear data only when requested

**Implementation Notes:**
- Use efficient JSON format for interlinear data storage and retrieval
- Implement caching for frequently requested interlinear verses
- Ensure graceful degradation when morphological data is incomplete

#### Task 10.2: Essential Analytics System Implementation
**Priority:** Medium
**Estimated Effort:** 6 hours
**Dependencies:** Phase 1 Complete

**Acceptance Criteria:**
- [ ] Implement basic analytics middleware to capture tool usage and performance metrics
- [ ] Track essential KPIs: daily active users, tool usage frequency, response times, error rates
- [ ] Monitor biblical research patterns: popular books, translation preferences, search success rates
- [ ] Create simple performance dashboard for service monitoring and optimization
- [ ] Ensure privacy-compliant data collection with no PII or theological content storage

**Implementation Notes:**
- Use lightweight analytics (SQLite for metrics storage initially)
- Focus on actionable metrics that directly impact service quality
- Simple dashboard using built-in web framework or basic HTML/JavaScript

#### Task 10.3: Community Impact Tracking (Optional)
**Priority:** Low
**Estimated Effort:** 4 hours
**Dependencies:** Task 10.2

**Acceptance Criteria:**
- [ ] Track basic community metrics: geographic distribution (country-level), MCP client usage
- [ ] Monitor service health: uptime, availability, peak usage times
- [ ] Create simple growth tracking: new users, retention patterns
- [ ] Add basic alerting for service issues (error spikes, downtime)
- [ ] Generate monthly community impact reports

**Implementation Notes:**
- Keep it simple - focus on metrics that help you understand if the service is valuable
- Use free monitoring tools (basic Grafana, simple email alerts)
- Only implement if you want to track community growth and impact

## Implementation Guidelines

### Development Workflow

1. **Task Prioritization:** Complete Phase 1 tasks in order before starting Phase 2
2. **Testing Strategy:** Write tests alongside implementation, not as an afterthought
3. **Documentation:** Update documentation as features are implemented
4. **Code Review:** All tasks should include code review checklist items
5. **Performance:** Monitor database query performance and optimize as needed

### Quality Standards

- **Code Coverage:** Maintain 90%+ test coverage for all core functionality
- **Performance:** Ensure startup time under 100ms and search responses under 500ms
- **Error Handling:** All error conditions must be tested and handled gracefully
- **Documentation:** All public APIs must have comprehensive documentation
- **Theological Accuracy:** All biblical data must be validated against authoritative sources

### Deployment Strategy

- **Phase 1 Deployment:** Simple hosted service on Render/Railway with Docker container
- **Database Distribution:** Include optimized SQLite database in container image
- **Monitoring:** Implement basic health checks and error monitoring
- **Scaling:** Design for horizontal scaling if usage grows significantly

This task breakdown provides a clear roadmap for implementing SolaGuard as a robust, theologically sound MCP server that serves as universal infrastructure for Scripture-grounded AI applications.