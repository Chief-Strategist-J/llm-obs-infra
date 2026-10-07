# Universal Architecture & Engineering Refactoring Checklist

> Standard operational checklist for engineering, refactoring, and verifying domain algorithms, database adapters, query registries, and REST APIs across the codebase.

---

## 1. Domain Algorithm & Purity Layer

- [x] **Generic Data Modeling (`TypeVar(T)`)**
  - Abstract algorithm interfaces from concrete primitives (`str`, `int`).
  - Allow arbitrary caller models: custom classes, dataclasses, Pydantic entities, or tuples.
  - Support custom hashable identifier extractors (`key_fn: Callable[[T], Any]`).

- [x] **Lazy & Dynamic Neighbor Expansion**
  - Support on-demand generator / callable expansion (`get_neighbors: Callable[[T], Iterable[Tuple[T, float]]]` or `Callable[[T], Iterable[T]]`).
  - Eliminate memory bottlenecks by avoiding pre-loading billion-node graphs into memory.

- [x] **Dynamic Scoring & ML Heuristics**
  - Accept dynamic scoring callables (`heuristic_fn: Callable[[T], float]`) for neural embeddings, vector distances (cosine/Euclidean), or runtime coordinates.
  - Avoid hardcoded static lookup dictionaries.

- [x] **Hexagonal Port & Protocol Abstraction**
  - Declare structural protocols (`@runtime_checkable class GraphNeighborProvider(Protocol[T])`) and store port bridges (`*_with_store(store: GraphStorePort)`).
  - Enable plug-and-play integration for any third-party database (Neo4j, Memgraph, Neptune, ArangoDB, Postgres AGE, SQLite) with zero vendor lock-in.

- [x] **Zero-Inline-Comment Doctrine**
  - Function and method bodies must remain 100% comment-free and self-documenting.
  - Complete algorithm blueprint, time/space complexity, preconditions, and operational invariants declared in top-level file headers and YAML docblock contracts.

- [x] **Backward Compatibility**
  - Preserve legacy method signatures so existing tests and consumers continue to function without breaking.

---

## 2. Query Architecture & Storage Layer

- [x] **Dedicated Queries Directory Structure**
  - Query definitions reside in `src/features/code_engine/queries/knowledge_graph/analytics/`.
  - Prohibit scattered or inline query strings across service, repository, or algorithm files.

- [x] **Standardized Query Naming Formula (Rule 2.4 & Rule 3.7)**
  - All query constants follow the semantic formula:
    $$\text{FLOW\_}\{\text{VERB}\}\_\{\text{ENTITY}\}\_\{\text{CRITERIA}\}$$
  - Examples: `FLOW_GET_PROJECTED_ASTAR_SHORTEST_PATH`, `FLOW_GET_PROCEDURE_ASTAR_SHORTEST_PATH`, `FLOW_GET_DEGREE_CENTRALITY`, `FLOW_GET_CONNECTED_COMPONENTS`, `FLOW_GET_LOUVAIN_COMMUNITIES`.

- [x] **Dual Artifact Specification (`.sql` & `.py`)**
  - Store raw parameterized DDL/Cypher/SQL in `{feature}.queries.sql`.
  - Export strongly typed, immutable Python string constants in `{feature}_queries.py`.

- [x] **Strict Parameterization**
  - Always parameterize dynamic values via key-value parameter maps to prevent injection and separate logic from runtime values.

---

## 3. Delivery & REST API Layer

- [x] **Contract-First OpenAPI Specification**
  - Commit all new endpoints and request/response DTO schemas to `contracts/openapi/v1.yaml`.

- [x] **Strongly Typed Pydantic DTOs**
  - Declare explicit field types, default values, and schema descriptions for all incoming request payloads.

- [x] **Standardized Response Envelope**
  - Wrap all API responses in the canonical JSON response envelope:
    ```json
    {
      "data": { ... },
      "error": null,
      "meta": { "trace_id": "..." }
    }
    ```

- [x] **End-to-End Distributed Tracing**
  - Extract and propagate OpenTelemetry W3C trace contexts (`x-trace-id`, `traceparent`) across network boundaries.

---

## 4. Package Structure & Module Resolution

- [x] **Package Marker Initialization (`__init__.py`)**
  - Ensure every directory in the package tree contains an `__init__.py` file for Python module resolution and Pyright static analysis.

- [x] **Explicit Module Exports (`__all__`)**
  - Define `__all__` lists in package `__init__.py` files to expose public APIs and encapsulate internal utilities.

- [x] **Strict Static Typing**
  - Ensure zero type checker errors, eliminating redundant casts and untyped union attribute accesses.

---

## 5. Verification & Test Suite

- [x] **Comprehensive Unit Tests**
  - Validate core algorithm correctness on weighted graphs.
  - Test custom dataclass/Pydantic entities with dynamic heuristics.
  - Test query plan generation and parameter binding.
  - Test mock third-party database adapters (`GraphStorePort`).

- [x] **Full Regression Suite**
  - 100% test pass rate across unit test suite (609/609 tests passing).

---

## 6. Completed Knowledge Graph Analytics Algorithms Matrix (21/21)

| Algorithm Name | Contract ID | Generic `TypeVar(T)` | Store Adapter Bridge | Parameterized Named Query |
|---|---|---|---|---|
| `KgAlgoAstarSearch` | `ALGO-KG-67` | Yes (`search_generic`) | Yes (`search_with_store`) | `FLOW_GET_PROJECTED_ASTAR_SHORTEST_PATH` |
| `KgAlgoBfsTraversal` | `ALGO-KG-63` | Yes (`traverse_generic`) | Yes (`traverse_with_store`) | `FLOW_GET_BFS_TRAVERSAL` |
| `KgAlgoDfsTraversal` | `ALGO-KG-64` | Yes (`traverse_generic`) | Yes (`traverse_with_store`) | `FLOW_GET_DFS_TRAVERSAL` |
| `KgAlgoBidirectionalBfs` | `ALGO-KG-65` | Yes (`find_shortest_path_generic`) | Yes (`find_shortest_path_with_store`) | `FLOW_GET_BIDIRECTIONAL_BFS_PATH` |
| `KgAlgoDijkstraShortestPath` | `ALGO-KG-66` | Yes (`compute_distances_generic`) | Yes (`compute_distances_with_store`) | `FLOW_GET_DIJKSTRA_SHORTEST_PATH` |
| `KgAlgoYensKShortestPaths` | `ALGO-KG-68` | Yes (`find_k_paths_generic`) | Yes (`find_k_paths_with_store`) | `FLOW_GET_YENS_K_SHORTEST_PATHS` |
| `KgAlgoDegreeCentrality` | `ALGO-KG-73` | Yes (`compute_centrality_generic`) | Yes (`compute_centrality_with_store`) | `FLOW_GET_DEGREE_CENTRALITY` |
| `KgAlgoPagerankCentrality` | `ALGO-KG-74` | Yes (`compute_pagerank_generic`) | Yes (`compute_pagerank_with_store`) | `FLOW_GET_PAGERANK_CENTRALITY` |
| `KgAlgoPersonalizedPagerank` | `ALGO-KG-75` | Yes (`compute_ppr_generic`) | Yes (`compute_ppr_with_store`) | `FLOW_GET_PERSONALIZED_PAGERANK` |
| `KgAlgoBrandesBetweenness` | `ALGO-KG-76` | Yes (`compute_betweenness_generic`) | Yes (`compute_betweenness_with_store`) | `FLOW_GET_BETWEENNESS_CENTRALITY` |
| `KgAlgoClosenessHarmonic` | `ALGO-KG-77` | Yes (`compute_harmonic_generic`) | Yes (`compute_harmonic_with_store`) | `FLOW_GET_HARMONIC_CLOSENESS` |
| `KgAlgoHitsCentrality` | `ALGO-KG-78` | Yes (`compute_hits_generic`) | Yes (`compute_hits_with_store`) | `FLOW_GET_HITS_CENTRALITY` |
| `KgAlgoConnectedComponents` | `ALGO-KG-79` | Yes (`find_components_generic`) | Yes (`find_components_with_store`) | `FLOW_GET_CONNECTED_COMPONENTS` |
| `KgAlgoTarjanScc` | `ALGO-KG-80` | Yes (`compute_scc_generic`) | Yes (`compute_scc_with_store`) | `FLOW_GET_STRONGLY_CONNECTED_COMPONENTS` |
| `KgAlgoLouvainCommunity` | `ALGO-KG-81` | Yes (`detect_communities_generic`) | Yes (`detect_communities_with_store`) | `FLOW_GET_LOUVAIN_COMMUNITIES` |
| `KgAlgoLeidenCommunity` | `ALGO-KG-82` | Yes (`refine_communities_generic`) | Yes (`refine_communities_with_store`) | `FLOW_GET_LEIDEN_COMMUNITIES` |
| `KgAlgoLabelPropagation` | `ALGO-KG-83` | Yes (`propagate_labels_generic`) | Yes (`propagate_labels_with_store`) | `FLOW_GET_LABEL_PROPAGATION` |
| `KgAlgoKCoreDecomposition` | `ALGO-KG-84` | Yes (`extract_k_core_generic`) | Yes (`extract_k_core_with_store`) | `FLOW_GET_K_CORE_DECOMPOSITION` |
| `KgAlgoRandomWalkRestart` | `ALGO-KG-69` | Yes (`run_walk_generic`) | Yes (`run_walk_with_store`) | `FLOW_GET_RANDOM_WALK_RESTART` |
| `KgAlgoMetapathTraversal` | `ALGO-KG-70` | Yes (`traverse_metapath_generic`) | Yes (`traverse_metapath_with_store`) | `FLOW_GET_METAPATH_TRAVERSAL` |
| `KgAlgoTwoHopLabeling` | `ALGO-KG-71` | Yes (`is_reachable_generic`) | Yes (`is_reachable_with_store`) | `FLOW_GET_TWO_HOP_REACHABILITY` |
| `KgAlgoTransitiveClosure` | `ALGO-KG-72` | Yes (`compute_closure_generic`) | Yes (`compute_closure_with_store`) | `FLOW_GET_TRANSITIVE_CLOSURE` |
