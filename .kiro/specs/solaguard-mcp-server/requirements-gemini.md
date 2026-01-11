# SolaGuard MCP - Technical Requirements & Architecture

## 1. Vision & Strategy
*   **Model:** Open Core (Freemium).
*   **Core Promise:** A reliable, Protestant-aligned theological layer for AI, adhering to Sola Scriptura.
*   **Distribution:**
    *   **Free (OSS):** Local SQLite DB, Public Domain Texts (KJV, WEB, TR, WLC), CLI execution.
    *   **Paid (Future):** Hosted SaaS (SSE endpoint) for non-technical users, Licensed Texts (ESV/NIV) via royalty agreements, Premium Audio (ElevenLabs).

## 2. Technical Architecture
*   **Language:** Python 3.10+
*   **Framework:** `mcp` (Model Context Protocol SDK), `fastmcp`.
*   **Storage (Runtime):** SQLite (`solaguard.db`).
    *   **Rationale:** Solves the "Startup Time vs. Memory" trade-off.
    *   **Benefits:** Instant startup (no JSON parsing), zero RAM overhead for idle server, built-in FTS5 (Full Text Search) for fast queries.
*   **Ingestion Pipeline:**
    *   Decoupled from runtime server.
    *   Scripts (`scripts/build_db.py`) ingest raw source data (JSON/XML) and compile an optimized, immutable `.db` artifact.
    *   Server treats the DB as read-only.

## 3. Data Schema (SQLite)

### Core Tables
*   **`translations`**
    *   `id` (PK, Text): e.g., "KJV", "TR", "WEB".
    *   `name` (Text): e.g., "King James Version".
    *   `language` (Text): "en", "grc", "hbo".
    *   `type` (Text): "translation" or "original".

*   **`verses`**
    *   `id` (PK, Integer): Auto-inc.
    *   `translation_id` (FK, Text).
    *   `book_id` (Text): Standard 3-letter code (e.g., 'GEN', 'JHN').
    *   `chapter` (Integer).
    *   `verse` (Integer).
    *   `text` (Text): Plain text content for display and reading.
    *   *Index:* Compound index on `(translation_id, book_id, chapter, verse)`.

*   **`verses_fts` (Virtual Table)**
    *   FTS5 virtual table indexing `verses.text` for sub-millisecond keyword search.

*   **`words` (Interlinear Data)**
    *   `id` (PK, Integer).
    *   `verse_id` (FK, Integer).
    *   `sequence` (Integer): Word order (1, 2, 3...).
    *   `text` (Text): The raw word token (Greek/Hebrew/English).
    *   `normalized` (Text): Lowercase/lemma form.
    *   `strongs` (Text): e.g., "G25", "H1234".
    *   `morphology` (JSON): e.g., `{"pos": "verb", "tense": "aorist"}`.
    *   `english_equiv` (Text): Aligned English translation (if applicable).

## 4. MCP Tools Specification

### Tool 1: `get_verse`
*   **Signature:** `get_verse(reference: str, translation: str = "KJV", include_interlinear: bool = False)`
*   **Logic:**
    1.  Parse standard reference (e.g., "John 3:16", "Gn 1:1").
    2.  Query `verses` table.
    3.  (Optional) If `include_interlinear=True`, lazy-load related rows from `words` table.
*   **Output:** Formatted text or detailed JSON structure.

### Tool 2: `search_scripture`
*   **Signature:** `search_scripture(query: str, translation: str = "KJV", limit: int = 10)`
*   **Logic:**
    1.  Execute SQL: `SELECT ... FROM verses_fts WHERE text MATCH {query}`.
    2.  Rank by relevance (BM25 built into SQLite).
*   **Output:** List of matching verses with references.

### Tool 3: `doctrinal_check` (Prototype)
*   **Signature:** `doctrinal_check(topic: str)`
*   **Logic:**
    1.  (Phase 1) Perform keyword search on topic terms.
    2.  (Phase 2) Look up topic in a `topics` table (curated mapping).
    3.  Return raw relevant scripture to the LLM to perform the final consistency analysis.

## 5. Development Roadmap

### Phase 1: The Foundation (Local MVP)
*   **Goal:** A working CLI server querying a local SQLite DB.
*   **Tasks:**
    1.  Define `pydantic` models for API responses.
    2.  Create `db.py` to manage SQLite connection.
    3.  Create `scripts/build_db.py` to create tables and load mock data.
    4.  Implement `server.py` with `get_verse` and `search_scripture`.

### Phase 2: Data Engineering (The Hard Part)
*   **Goal:** Replace mock data with real Public Domain texts.
*   **Tasks:**
    1.  Source KJV and WEB JSONs.
    2.  Source OpenScriptures (Greek/Hebrew) data.
    3.  Update ingestion scripts to process these massive files.

### Phase 3: SaaS Readiness
*   **Goal:** Prepare for "Open Core" monetization.
*   **Tasks:**
    1.  Add API Key authentication middleware.
    2.  Create `Dockerfile` for hosted deployment.

## 6. Constraints & Standards
*   **Dependencies:** Minimal runtime deps. `mcp`, `pydantic`. (`uvicorn` only for SaaS mode).
*   **Licensing:** 
    *   Code: MIT License.
    *   Data: Must track attribution for OpenScriptures/CC-BY-SA sources in a `NOTICE` file.
*   **Error Handling:** Graceful failures. Never crash the server on bad input. Return clear error strings to the LLM.
