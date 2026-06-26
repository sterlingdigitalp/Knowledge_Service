# Architecture — Layered Platform Specification

## Purpose

This document defines the complete layered architecture of Knowledge_Service. It specifies each layer's responsibilities, interfaces, data flow, and boundaries. This is the primary reference for understanding how the system is structured and how components interact.

## Scope

This document covers:
- The six architectural layers and their responsibilities
- Inter-layer communication patterns
- Extension points for future capabilities
- Data flow through the platform
- Deployment topology considerations

## Design Rationale

The architecture uses a layered model because it provides:
- **Clear ownership**: Each layer has exactly one responsibility
- **Testability**: Layers can be tested in isolation using mocks of adjacent layers
- **Replaceability**: Internal components within a layer can be replaced without affecting other layers
- **Evolution**: New capabilities are added by extending existing layers or adding new ones, not by modifying existing code

The layered model was chosen over event-driven or microservice architectures for Phase 0 because:
1. It provides clearer boundaries for the initial implementation
2. It reduces operational complexity while maintaining extensibility
3. Layers can later be decomposed into services if scale demands it
4. The interface contracts between layers remain valid regardless of deployment topology

## Architectural Layers

```
┌─────────────────────────────────────────────────────────┐
│                    Application Layer                     │
│         (Hermes, BuilderBoard, Arete, etc.)             │
└────────────────────────┬────────────────────────────────┘
                         │  HTTP/gRPC API calls
┌────────────────────────▼────────────────────────────────┐
│                   API Layer                              │
│   Authentication · Validation · Routing · Versioning    │
└────────────────────────┬────────────────────────────────┘
                         │  Internal requests
┌────────────────────────▼────────────────────────────────┐
│                 Planning Layer                           │
│  Strategy · Provider Selection · Orchestration          │
└────────────────────────┬────────────────────────────────┘
                         │  Acquisition plans
┌────────────────────────▼────────────────────────────────┐
│               Acquisition Layer                          │
│  Fetch · Download · Query · Stream                      │
└────────────────────────┬────────────────────────────────┘
                         │  Raw content + metadata
┌────────────────────────▼────────────────────────────────┐
│               Processing Layer                           │
│  Clean · Normalize · Extract · Chunk · Enrich           │
└────────────────────────┬────────────────────────────────┘
                         │  Knowledge Objects
┌────────────────────────▼────────────────────────────────┐
│                Knowledge Layer                           │
│  Store · Retrieve · Index · Cache · Graph               │
└────────────────────────┬────────────────────────────────┘
                         │  Provider calls
┌────────────────────────▼────────────────────────────────┐
│                Provider Layer                            │
│  Crawl4AI · SearXNG · GitHub · RSS · Vector DBs         │
└─────────────────────────────────────────────────────────┘
```

## Layer Definitions

### API Layer

**Responsibility**: Public interface for all external communication.

**Ownership**: Request lifecycle management, authentication, validation, routing, response formatting, rate limiting, and versioning.

**Inputs**: HTTP/gRPC requests from applications.

**Outputs**: Structured responses containing Knowledge Objects or operation status.

**Internal Interface**: Translates API requests into internal planning requests understood by the Planning Layer.

**Responsibilities**:
- Authenticate application clients
- Validate request parameters against schema
- Rate limit and throttle incoming requests
- Route requests to appropriate planning strategies
- Format responses according to API version contracts
- Manage API key lifecycle and permissions
- Return standardized error responses with trace IDs

**Non-responsibilities**:
- Knowledge acquisition logic (Planning Layer)
- Content processing (Processing Layer)
- Storage decisions (Knowledge Layer)
- Provider selection details (Planning Layer)

**Extension Points**:
- New endpoint types (REST, GraphQL, gRPC)
- Authentication methods (API keys, OAuth, mTLS)
- Response formats (JSON, protobuf, SSE for streaming)

### Planning Layer

**Responsibility**: Determine how to acquire requested knowledge.

**Ownership**: Strategy selection, provider orchestration, fallback planning, and acquisition coordination.

**Inputs**: Knowledge requests from the API Layer.

**Outputs**: Acquisition plans executed by the Acquisition Layer; final assembled results returned through the Processing and Knowledge Layers.

**Internal Interface**: Defines `Planner` interface that accepts a knowledge request and produces an acquisition plan with provider selections, ordering, and fallback strategies.

**Responsibilities**:
- Analyze knowledge requests to determine required information sources
- Select appropriate providers based on content type, source quality, and availability
- Determine acquisition order (parallel vs sequential)
- Define stopping conditions (when enough evidence has been gathered)
- Plan fallback behavior when primary providers fail
- Coordinate multi-source acquisition and result assembly
- Apply freshness requirements to acquisition strategy

**Non-responsibilities**:
- Actual content fetching (Acquisition Layer)
- Content normalization (Processing Layer)
- Storage decisions (Knowledge Layer)
- Source quality evaluation (Source Registry, consulted by Planning Layer)

**Extension Points**:
- New planning strategies (greedy, constraint-based, learning-based)
- New provider selection heuristics
- Custom stopping conditions per use case
- Multi-step acquisition chains with conditional branching

### Acquisition Layer

**Responsibility**: Fetch raw content from providers.

**Ownership**: Provider communication, content retrieval, error handling at fetch time, and raw response collection.

**Inputs**: Acquisition plans from the Planning Layer.

**Outputs**: Raw content (HTML, JSON, XML, binary) with provider-attached metadata.

**Internal Interface**: Calls providers through the Provider Interface; returns raw content bundles to the Processing Layer.

**Responsibilities**:
- Execute acquisition plans by calling appropriate providers
- Handle network-level errors (timeouts, connection failures)
- Apply rate limiting and backoff per provider configuration
- Collect raw responses from multiple providers
- Attach acquisition context (timestamp, request ID, plan reference) to each response
- Report acquisition status (success, partial, failed) with per-provider results

**Non-responsibilities**:
- Content interpretation or parsing (Processing Layer)
- Provider implementation details (Provider Layer)
- Knowledge object construction (Processing Layer)
- Storage decisions (Knowledge Layer)

**Extension Points**:
- New acquisition modes (streaming, batch, incremental)
- New retry strategies (exponential backoff, jitter, fixed)
- New concurrency models (async, parallel, sequential)

### Processing Layer

**Responsibility**: Normalize raw content into canonical Knowledge Objects.

**Ownership**: Content cleaning, markdown conversion, metadata extraction, chunking, relationship detection, and enrichment.

**Inputs**: Raw content bundles from the Acquisition Layer.

**Outputs**: Canonical Knowledge Objects ready for storage in the Knowledge Layer.

**Internal Interface**: Defines `Processor` interface that accepts raw content and produces one or more Knowledge Objects.

**Responsibilities**:
- Clean and normalize raw HTML/content
- Convert diverse formats to canonical markdown representation
- Extract structured metadata (title, authors, dates, language)
- Detect and extract citations and references
- Compute content hashes for deduplication
- Chunk content into retrievable units while preserving context
- Detect relationships between knowledge objects
- Attach confidence scores based on source quality and completeness
- Enrich with semantic metadata where applicable

**Non-responsibilities**:
- Content acquisition (Acquisition Layer)
- Storage decisions (Knowledge Layer)
- Provider selection (Planning Layer)
- Strategic planning (Planning Layer)

**Extension Points**:
- New content format handlers (PDF, video transcripts, audio)
- New extraction strategies (LLM-based, rule-based, hybrid)
- New chunking algorithms (semantic, fixed-size, hierarchical)
- New enrichment capabilities (entity extraction, topic classification)

### Knowledge Layer

**Responsibility**: Persistent storage and retrieval of knowledge.

**Ownership**: Storage backend management, indexing, caching, retrieval queries, and knowledge graph maintenance.

**Inputs**: Knowledge Objects from the Processing Layer.

**Outputs**: Knowledge Objects or projections returned to requesting applications.

**Internal Interface**: Defines `KnowledgeStore` interface for CRUD operations on Knowledge Objects; defines `Retriever` interface for search and query operations.

**Responsibilities**:
- Store Knowledge Objects with full evidence and metadata
- Index content for retrieval (full-text, vector, graph)
- Manage cache layers for frequently accessed knowledge
- Execute retrieval queries from the API Layer
- Maintain knowledge graph relationships
- Handle deduplication at storage time
- Manage knowledge lifecycle (active, archived, expired)
- Provide consistency guarantees per storage backend

**Non-responsibilities**:
- Content acquisition or processing (Acquisition + Processing Layers)
- Provider communication (Provider Layer)
- Strategic planning (Planning Layer)
- API request handling (API Layer)

**Extension Points**:
- New storage backends (PostgreSQL, MongoDB, Neo4j, etc.)
- New indexing strategies (BM25, dense vectors, hybrid)
- New cache implementations (Redis, Memcached, in-memory)
- New graph traversal algorithms

### Provider Layer

**Responsibility**: Communicate with external systems to acquire content.

**Ownership**: Provider SDK integration, credential management, provider-specific error handling, and capability exposure.

**Inputs**: Requests from the Acquisition Layer through the Provider Interface.

**Outputs**: Raw content responses conforming to the Provider Interface contract.

**Internal Interface**: Implements the `Provider` interface defined in PROVIDER_INTERFACE.md. This is the ONLY interface that crosses between Knowledge_Service internals and external systems.

**Responsibilities**:
- Implement provider-specific communication protocols
- Manage provider credentials and authentication
- Handle provider-specific error formats and rate limits
- Expose provider capabilities through a uniform interface
- Report provider health status
- Cache provider responses where appropriate

**Non-responsibilities**:
- Strategic decisions about which providers to use (Planning Layer)
- Content interpretation or normalization (Processing Layer)
- Storage of knowledge objects (Knowledge Layer)
- API request handling from applications (API Layer)

**Extension Points**:
- New provider implementations (any external system with data)
- New capability types within existing providers
- Provider-specific optimization hooks

## Inter-Layer Communication

### Data Flow Pattern

```
Request → API Layer → Planning Layer → Acquisition Layer → Raw Content
Raw Content → Processing Layer → Knowledge Objects → Knowledge Layer → Storage
Response ← Knowledge Layer ← Processing Layer (enrichment) ← API Layer ← Application
```

Each layer passes data to the next layer through well-defined interfaces. No layer skips another. No layer accesses layers beyond its immediate neighbor.

### Communication Contracts

| From | To | Contract Type | Format |
|------|-----|--------------|--------|
| Application | API Layer | Public API (HTTP/gRPC) | JSON/Protobuf |
| API Layer | Planning Layer | Internal request object | Typed interface |
| Planning Layer | Acquisition Layer | Acquisition plan | Typed interface |
| Acquisition Layer | Processing Layer | Raw content bundle | Typed interface |
| Processing Layer | Knowledge Layer | Knowledge Object | Typed interface |
| Knowledge Layer | API Layer | Query result set | Typed interface |

### Error Propagation

Errors propagate upward through layers:
1. Provider errors are caught and normalized in the Acquisition Layer
2. Processing failures produce partial results with reduced confidence
3. Storage failures trigger retry or fallback mechanisms
4. The API Layer returns standardized error responses to applications

Each layer adds its own context to errors without exposing internal implementation details to layers above it.

## Data Ownership Per Layer

| Layer | Owns | Does Not Own |
|-------|------|--------------|
| API Layer | Request/response lifecycle, auth state | Knowledge content, provider credentials |
| Planning Layer | Acquisition strategies, plans | Raw content, storage format |
| Acquisition Layer | Raw responses, fetch metadata | Normalized content, knowledge objects |
| Processing Layer | Knowledge Objects, enrichment data | Provider-specific formats, raw HTML |
| Knowledge Layer | Persistent storage, indexes, cache | Acquisition strategy, API contracts |
| Provider Layer | Provider SDKs, credentials, raw responses | Application code, business logic |

## Deployment Topology

### Single-Instance (Development)

All layers run in a single process. Layers are separated by package/module boundaries rather than network boundaries. This is suitable for development and testing.

### Multi-Process (Production)

Layers may be deployed as separate processes within the same service:
- API Layer runs as a stateless gateway
- Planning + Acquisition + Processing layers run as application workers
- Knowledge Layer connects to external storage services
- Provider Layer runs within application workers (no separate deployment needed)

### Distributed (Scale)

At sufficient scale, individual layers may be deployed as independent services:
- API Layer scales horizontally with load balancers
- Planning Layer maintains state for long-running acquisition chains
- Acquisition Layer scales with provider concurrency requirements
- Processing Layer scales with content volume
- Knowledge Layer connects to distributed storage backends

The layer interfaces remain identical regardless of deployment topology. This document does not prescribe a specific topology; it defines the boundaries that must be respected in any topology.

## Extension Architecture

### Adding a New Provider

1. Implement the `Provider` interface in the Provider Layer
2. Register the provider in the Source Registry
3. Configure provider credentials and capabilities
4. No changes required to higher layers

### Adding a New API Endpoint

1. Define endpoint schema and response format in API Layer
2. Map endpoint to appropriate planning strategy in Planning Layer
3. Ensure Processing Layer can produce required output format
4. No changes required to Acquisition or Provider Layers (unless new provider is needed)

### Adding a New Content Type

1. Add content handler in Processing Layer
2. Update Knowledge Object schema if new metadata fields are required
3. Register new capability in relevant providers
4. No changes required to API Layer or Planning Layer (if existing planning strategies cover the type)

### Adding a New Storage Backend

1. Implement `KnowledgeStore` interface for the new backend
2. Migrate data from existing backends if needed
3. Update configuration to select backend
4. No changes required to higher layers

## Design Decisions and Tradeoffs

### Layered vs Event-Driven

**Decision**: Layered architecture for Phase 0.

**Rationale**: Clearer boundaries, easier testing, simpler debugging. The layer interfaces can later be adapted to event-driven patterns if throughput demands it.

**Tradeoff**: Slightly higher latency due to synchronous calls between layers versus asynchronous event processing. Acceptable for the expected initial scale.

### Monolithic vs Microservice Deployment

**Decision**: Layered monolith with clear internal boundaries.

**Rationale**: Simpler development and deployment while maintaining architectural clarity. Layers can be decomposed into services later without interface changes.

**Tradeoff**: Less independent scalability per layer at early stages. Acceptable because the cost of premature decomposition exceeds the benefit for initial scale.

### Synchronous vs Asynchronous Processing

**Decision**: Synchronous request-response for immediate knowledge requests; asynchronous processing for long-running acquisition chains.

**Rationale**: Most application requests are synchronous (request knowledge, receive answer). Some acquisitions (deep research, periodic updates) benefit from async processing. Both patterns are supported through the same layer interfaces.

**Tradeoff**: Async operations require additional state management. This is handled by the Planning Layer's orchestration capabilities.

## Assumptions

- Knowledge_Service will serve multiple concurrent applications
- Provider availability varies and must be handled gracefully
- The volume of knowledge to store and retrieve will grow over time
- Applications have varying latency requirements (some need immediate results, some can wait)
- Storage backends may be local or cloud-hosted

## Future Evolution

Phase 0 establishes the layered foundation. Future phases will:
1. Implement each layer according to these specifications
2. Add concrete provider implementations
3. Define specific storage backend integrations
4. Implement planning strategies with increasing sophistication
5. Add observability and monitoring infrastructure

The layer boundaries defined here remain stable through all future evolution. New capabilities extend within layers or add new layers; they do not restructure existing ones.
