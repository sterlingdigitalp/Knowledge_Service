# System Diagram — Architecture Visualizations

## Purpose

This document provides visual representations of the Knowledge_Service architecture through Mermaid diagrams. These diagrams illustrate system components, data flow, knowledge lifecycle, and layer interactions. They serve as a quick-reference complement to the detailed specifications in other documents.

## Scope

This document contains:
- High-level system context diagram
- Layer interaction diagram
- Knowledge acquisition flow diagram
- Knowledge object lifecycle diagram
- Provider abstraction diagram
- Data storage architecture diagram
- Error handling and fallback flow diagram

All diagrams use Mermaid syntax for rendering in Markdown-compatible viewers.

## Diagram 1: System Context

Shows the relationship between applications, Knowledge_Service, and external providers.

```mermaid
graph TB
    subgraph Applications["Application Layer"]
        Hermes[Hermes]
        BuilderBoard[BuilderBoard]
        Arete[Arete]
        SearchAgent[SearchAgent]
        PepFox[PepFox]
        DirectorDesk[Director Desk]
        OpportunityScanner[Opportunity Scanner]
        FutureApp[Future Application]
    end

    subgraph KnowledgeService["Knowledge_Service Platform"]
        API[API Layer<br/>Auth · Validation · Routing]
        Planning[Planning Layer<br/>Strategy · Orchestration]
        Acquisition[Acquisition Layer<br/>Fetch · Download · Query]
        Processing[Processing Layer<br/>Clean · Normalize · Chunk]
        Knowledge[Knowledge Layer<br/>Store · Retrieve · Index]
    end

    subgraph Providers["Provider Layer"]
        Crawl4AI[Crawl4AI]
        SearXNG[SearXNG]
        GitHubAPI[GitHub API]
        RSS[RSS Feeds]
        VectorDB[Vector Database<br/>Qdrant / Alternative]
        LLM[LLM Provider<br/>OpenAI / Local / Alternative]
        PDFHandler[PDF Processor]
        YouTube[YouTube API]
        DBConnector[Database Connector]
    end

    Hermes -->|Knowledge Request| API
    BuilderBoard -->|Documentation Request| API
    Arete -->|Research Query| API
    SearchAgent -->|Search Request| API
    PepFox -->|Data Request| API
    DirectorDesk -->|Analysis Request| API
    OpportunityScanner -->|Scan Request| API
    FutureApp -->|Any Request| API

    API --> Planning
    Planning --> Acquisition
    Acquisition --> Processing
    Processing --> Knowledge

    Acquisition -.->|Provider Calls| Crawl4AI
    Acquisition -.->|Provider Calls| SearXNG
    Acquisition -.->|Provider Calls| GitHubAPI
    Acquisition -.->|Provider Calls| RSS
    Acquisition -.->|Provider Calls| YouTube
    Acquisition -.->|Provider Calls| PDFHandler
    Acquisition -.->|Provider Calls| DBConnector

    Knowledge <-->|Store/Query| VectorDB
    Processing <-->|Enrichment| LLM

    style KnowledgeService fill:#e1f5fe,stroke:#01579b,stroke-width:3px
    style Providers fill:#fff3e0,stroke:#e65100,stroke-width:2px,stroke-dasharray: 5 5
    style Applications fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
```

**Legend:**
- Solid arrows: Direct data flow through defined interfaces
- Dashed arrows: Provider communication (abstracted through Provider Layer)
- Blue box: Knowledge_Service platform (the system being designed)
- Orange box: External providers (swappable, replaceable)
- Purple box: Applications (consumers, never access providers directly)

## Diagram 2: Layer Interaction

Shows how data flows through each layer during a knowledge request.

```mermaid
sequenceDiagram
    participant App as Application
    participant API as API Layer
    participant Plan as Planning Layer
    participant Acq as Acquisition Layer
    participant Proc as Processing Layer
    participant KB as Knowledge Layer
    participant Prov as Provider(s)

    App->>API: POST /knowledge {query, options}
    API->>API: Authenticate & validate request
    API->>Plan: KnowledgeRequest{query, options}

    Plan->>Plan: Analyze request scope
    Plan->>Plan: Select providers from Source Registry
    Plan->>Plan: Build acquisition plan
    Plan-->>API: AcquisitionPlan{providers, order, fallbacks}
    API-->>App: Acknowledged (sync) or returning...

    Note over Plan,Prov: Acquisition Phase
    Plan->>Acq: Execute plan
    Acq->>Prov: Fetch content (parallel/sequential)
    Prov-->>Acq: RawContent{html/json/binary}
    Acq->>Prov: Fetch additional sources
    Prov-->>Acq: RawContent{html/json/binary}

    Note over Proc,KB: Processing Phase
    Acq->>Proc: RawContentBundle[]
    Proc->>Proc: Clean & normalize
    Proc->>Proc: Extract metadata
    Proc->>Proc: Generate markdown
    Proc->>Proc: Chunk & enrich
    Proc->>Proc: Compute hashes & confidence
    Proc-->>API: KnowledgeObject[]

    Note over KB,App: Storage & Retrieval Phase
    API->>KB: Store KnowledgeObjects[]
    KB->>KB: Index for retrieval
    KB-->>API: Stored identifiers
    API-->>App: Response{KnowledgeObjects[], evidence}
```

**Key observations:**
1. The Application interacts only with the API Layer
2. Provider communication is entirely internal to Knowledge_Service
3. Each layer transforms data before passing it upward
4. Raw content enters at Acquisition; canonical objects exit at Processing
5. Evidence and metadata are attached progressively through processing

## Diagram 3: Knowledge Acquisition Flow

Shows the decision flow during knowledge acquisition, including fallback behavior.

```mermaid
flowchart TD
    Start[Knowledge Request Received] --> Validate{Request valid?}
    Validate -->|No| Error400[Return 400 Bad Request]
    Validate -->|Yes| Plan[Build Acquisition Plan]

    Plan --> CheckCache{Cache hit?<br/>fresh enough?}
    CheckCache -->|Yes| ReturnCached[Return cached knowledge]
    CheckCache -->|No| SelectProviders[Select providers<br/>from Source Registry]

    SelectProviders --> ExecutePlan[Execute acquisition plan]
    ExecutePlan --> ParallelFetch[{Parallel or<br/>sequential?}]

    ParallelFetch -->|Parallel| FetchAll[Fetch all providers<br/>concurrently]
    ParallelFetch -->|Sequential| FetchOne[Fetch primary provider]
    FetchOne --> CheckPrimary{Success?}
    CheckPrimary -->|Yes| ProcessContent
    CheckPrimary -->|No| Fallback1[Try fallback provider]
    Fallback1 --> CheckFallback1{Success?}
    CheckFallback1 -->|Yes| ProcessContent
    CheckFallback1 -->|No| TryNext[Try next fallback]

    FetchAll --> CollectResults[Collect all results]
    CollectResults --> HasAny{Any success?}

    TryNext --> CheckFallback2{More fallbacks?<br/>available?}
    CheckFallback2 -->|Yes| Fallback1
    CheckFallback2 -->|No| PartialResult

    HasAny -->|Yes| ProcessContent
    HasAny -->|No| PartialResult[Partial result with<br/>reduced confidence]

    ProcessContent[Process & normalize content] --> CreateObjects[Create Knowledge Objects]
    CreateObjects --> Store[Store in Knowledge Layer]
    Store --> ReturnFinal[Return knowledge + evidence]

    ReturnCached --> End([End])
    ReturnFinal --> End
    PartialResult --> ReturnPartial[Return partial with<br/>confidence warning]
    ReturnPartial --> End
    Error400 --> End([End])
```

## Diagram 4: Knowledge Object Lifecycle

Shows the complete lifecycle of a knowledge object from acquisition to archival.

```mermaid
stateDiagram-v2
    [*] --> Acquiring: Request received
    Acquiring --> RawContent: Provider responds
    RawContent --> Processing: Content normalized
    Processing --> Validating: Object created

    Validating --> Stored: Validation passed
    Validating --> Rejected: Validation failed
    Rejected --> [*]

    Stored --> Indexed: Indexing complete
    Indexed --> Active: Ready for retrieval

    Active --> Retrieved: Query matched
    Retrieved --> Active: Returned to consumer

    Active --> Stale: Freshness expired
    Stale --> RefreshRequired: Needs update
    RefreshRequired --> Acquiring: Re-acquisition scheduled

    Active --> Archived: Retention policy triggered
    Archived --> [*]

    note right of Acquiring
        Acquisition Layer fetches
        content from providers
    end note

    note right of Processing
        Processing Layer normalizes,
        extracts metadata, chunks
    end note

    note right of Indexed
        Knowledge Layer indexes
        for full-text and vector search
    end note

    note right of Archived
        Retention policy moves object
        to cold storage or deletes it
    end note
```

## Diagram 5: Provider Abstraction

Shows how the Provider Interface abstracts diverse external systems.

```mermaid
graph LR
    subgraph KnowledgeService["Knowledge_Service Internal"]
        AcqLayer[Acquisition Layer]
        ProviderInterface[Provider Interface<br/>initialize · execute · health · shutdown]
    end

    subgraph Providers["External Systems (Implement Interface)"]
        Crawl4AI_Impl[Crawl4AI Provider<br/>implements Provider]
        SearXNG_Impl[SearXNG Provider<br/>implements Provider]
        GitHub_Impl[GitHub Provider<br/>implements Provider]
        RSS_Impl[RSS Provider<br/>implements Provider]
        PDF_Impl[PDF Provider<br/>implements Provider]
        Custom_Impl[Custom Provider<br/>implements Provider]
    end

    AcqLayer --> ProviderInterface
    ProviderInterface --> Crawl4AI_Impl
    ProviderInterface --> SearXNG_Impl
    ProviderInterface --> GitHub_Impl
    ProviderInterface --> RSS_Impl
    ProviderInterface --> PDF_Impl
    ProviderInterface --> Custom_Impl

    style KnowledgeService fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    style Providers fill:#fff3e0,stroke:#e65100,stroke-width:2px,stroke-dasharray: 5 5
```

**Key insight:** The Acquisition Layer calls only the Provider Interface. It does not know or care which concrete provider implements it. Adding a new provider requires zero changes to the Acquisition Layer.

## Diagram 6: Data Storage Architecture

Shows how knowledge is stored across different storage backends.

```mermaid
graph TB
    subgraph KnowledgeLayer["Knowledge Layer"]
        Store[KnowledgeStore Interface]
        Indexer[Index Manager]
        CacheMgr[Cache Manager]
        GraphMgr[Graph Manager]
    end

    subgraph StorageBackends["Storage Backends (Pluggable)"]
        PrimaryDB[(Primary Store<br/>PostgreSQL / MongoDB)]
        VectorStore[(Vector Store<br/>Qdrant / Alternative)]
        CacheStore[(Cache Layer<br/>Redis / In-Memory)]
        GraphStore[(Graph Store<br/>Neo4j / Optional)]
    end

    subgraph KnowledgeObjects["Knowledge Objects"]
        KO1[Document 1<br/>+ Evidence + Citations]
        KO2[Document 2<br/>+ Evidence + Citations]
        KO3[Chunk A of Doc 1<br/>+ Parent Reference]
        KO4[Chunk B of Doc 1<br/>+ Parent Reference]
    end

    Store --> PrimaryDB
    Indexer --> VectorStore
    CacheMgr --> CacheStore
    GraphMgr --> GraphStore

    PrimaryDB --> KO1
    PrimaryDB --> KO2
    PrimaryDB --> KO3
    PrimaryDB --> KO4

    VectorStore -.->|Embeddings| KO1
    VectorStore -.->|Embeddings| KO2
    VectorStore -.->|Embeddings| KO3
    VectorStore -.->|Embeddings| KO4

    GraphStore -.->|Relationships| KO1
    GraphStore -.->|Relationships| KO2

    style KnowledgeLayer fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    style StorageBackends fill:#fff3e0,stroke:#e65100,stroke-width:2px
```

**Storage strategy:**
- **Primary Store**: Stores complete Knowledge Objects with full evidence and metadata
- **Vector Store**: Stores embeddings for semantic search (indexed by Knowledge Object ID)
- **Cache Layer**: Caches frequently accessed objects or query results
- **Graph Store**: Optional; stores relationship data between knowledge objects

The KnowledgeStore interface abstracts the primary store, allowing backend replacement without changing higher layers.

## Diagram 7: Error Handling and Fallback Flow

Shows how errors propagate through layers with graceful degradation.

```mermaid
flowchart TD
    subgraph ProviderLayer["Provider Layer"]
        P1[Provider A] -->|Success| OK1[RawContent]
        P1 -->|Error| E1[ProviderError{type}]
        P2[Provider B] -->|Success| OK2[RawContent]
        P2 -->|Error| E2[ProviderError{type}]

        E1 -->|Timeout| T1[Retry with backoff]
        E1 -->|Rate Limit| R1[Queue + wait]
        E1 -->|Auth Fail| A1[Mark provider unhealthy]
        E1 -->|Permanent| F1[Return error to caller]
    end

    subgraph AcquisitionLayer["Acquisition Layer"]
        T1 --> TryAgain{Retry success?}
        R1 --> TryAgain
        A1 --> SkipProvider[Skip this provider<br/>in plan]
        F1 --> CollectResults

        TryAgain -->|Yes| OK3[RawContent]
        TryAgain -->|No| Fail1[Record failure<br/>reduce confidence]

        OK1 --> CollectResults
        OK2 --> CollectResults
        OK3 --> CollectResults
    end

    subgraph ProcessingLayer["Processing Layer"]
        CollectResults{Any content?<br/>from any provider?}
        Fail1 --> CollectResults

        CollectResults -->|Yes| Process[Process available content]
        CollectResults -->|No| NoContent[Return error:<br/>no sources available]

        Process --> Validate{Processing<br/>successful?}
        Validate -->|Yes| Objects[KnowledgeObjects[]<br/>with reduced confidence]
        Validate -->|Partial| PartialObj[Partial KnowledgeObjects[]<br/>with warnings]
        Validate -->|Fail| ProcError[Return error with context]

        Objects --> ReturnResult
        PartialObj --> ReturnResult
    end

    subgraph APIResponse["API Layer Response"]
        ReturnResult{Result quality?}
        NoContent --> Err503[503 Service Unavailable<br/>+ which providers failed]
        ProcError --> Err500[500 Internal Error<br/>+ trace ID]
        ReturnResult -->|Full confidence| OK200[200 OK + full knowledge]
        ReturnResult -->|Reduced confidence| 200Partial[200 OK + partial knowledge<br/>+ confidence warning]

        Err503 --> End([End])
        Err500 --> End
        OK200 --> End
        200Partial --> End
    end

    style ProviderLayer fill:#ffebee,stroke:#c62828,stroke-width:1px
    style AcquisitionLayer fill:#fff3e0,stroke:#ef6c00,stroke-width:1px
    style ProcessingLayer fill:#fffde7,stroke:#f9a825,stroke-width:1px
    style APIResponse fill:#e8f5e9,stroke:#2e7d32,stroke-width:1px
```

**Error handling principles demonstrated:**
1. Provider errors are caught and normalized at the Provider/Acquisition boundary
2. Retries are attempted with configurable backoff policies
3. Failed providers are marked unhealthy to prevent repeated failures
4. Partial results are returned with confidence reduction rather than complete failure
5. Applications always receive structured responses indicating result quality

## Diagram 8: Source Registry Integration

Shows how the Source Registry feeds into planning decisions.

```mermaid
graph LR
    subgraph SourceRegistry["Source Registry"]
        SR_Trust[Trust Scores]
        SR_Fresh[Freshness Data]
        SR_Latency[Latency History]
        SR_Topics[Topic Expertise]
        SR_Cache[Cache Policies]
        SR_History[Historical Performance]
    end

    subgraph Planning["Planning Layer"]
        PS[Provider Selector]
        PO[Ordering Strategy]
        PF[Fallback Planner]
    end

    subgraph Acquisition["Acquisition Layer"]
        AC[Content Fetcher]
    end

    SR_Trust --> PS
    SR_Fresh --> PS
    SR_Latency --> PO
    SR_Topics --> PS
    SR_Cache --> PF
    SR_History --> PS

    PS -->|Selected providers with scores| AC
    PO -->|Acquisition order| AC
    PF -->|Fallback chain| AC

    style SourceRegistry fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    style Planning fill:#e1f5fe,stroke:#01579b,stroke-width:2px
```

**Key insight:** The Source Registry is consulted by the Planning Layer during plan construction. It provides historical data that informs provider selection, ordering, and fallback decisions. The registry accumulates experience over time (Principle 6: Accumulative Learning).

## Data Flow Summary

The diagrams collectively illustrate four primary data flows:

### Flow A: Knowledge Acquisition (Write Path)
```
Application → API Layer → Planning → Acquisition → Providers
Providers → Acquisition → Processing → Knowledge Objects → Knowledge Layer → Storage
```

### Flow B: Knowledge Retrieval (Read Path)
```
Application → API Layer → Knowledge Layer → Index/Cache/Graph → Knowledge Objects → Application
```

### Flow C: Source Learning (Feedback Loop)
```
Acquisition Results → Source Registry → Planning Decisions → Better Acquisition
```

### Flow D: Observability (Cross-Cutting)
```
Every Layer → Metrics Emitter → Monitoring System → Dashboards/Alerts
```

## Assumptions

- Mermaid is supported by the documentation viewer
- Diagrams are rendered at sufficient resolution to read all labels
- Color coding follows consistent semantics across diagrams (blue = platform, orange = external, purple = applications)

## Future Evolution

Future phases may add:
- Deployment topology diagrams showing container/orchestration structure
- Sequence diagrams for specific API endpoints
- State machine diagrams for knowledge object lifecycle states
- Network security diagrams showing credential isolation boundaries
- Performance architecture diagrams showing scaling considerations

These would extend, not replace, the diagrams in this document.
