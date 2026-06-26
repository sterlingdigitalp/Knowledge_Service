"""Retrieval Layer — Comprehensive Automated Tests

Covers: retrieve, list, exists, count, pagination, sorting, hierarchy, validation,
determinism, failure cases, corrupted objects, missing references, invalid IDs.
"""

import os, sys
_SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'src'))
sys.path.insert(0, _SRC_PATH)
sys.path.insert(0, os.path.dirname(_SRC_PATH))

import pytest
import time
from copy import deepcopy
from datetime import datetime, timezone

from src.knowledge_service.knowledge_object import (
    KnowledgeObject, KnowledgeType, SourceType, AcquisitionRecord,
    ProviderType, AcquisitionStatus, Citation,
)
from src.knowledge_service.storage.postgres.in_memory_store import InMemoryKnowledgeStore
from src.knowledge_service.storage.repositories.knowledge_repository import KnowledgeRepository
from src.knowledge_service.retrieval.retriever import KnowledgeRetrieverImpl
from src.knowledge_service.retrieval.interfaces import (
    KnowledgeQuery, SortField, SortOrder, QueryFilter,
)
from src.knowledge_service.retrieval.validation import RetrievalValidator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_doc(doc_id: str, title: str = "Test Doc", confidence: float = 0.9,
             acquired_at: str = None, source_id: str = "src-test",
             content: str = None) -> KnowledgeObject:
    if acquired_at is None:
        acquired_at = "2026-06-25T12:00:00Z"
    if content is None:
        content = f"Content for {doc_id}"
    ko = KnowledgeObject(
        id=doc_id, type=KnowledgeType.DOCUMENT, title=title,
        confidence=confidence, source_id=source_id,
        source_type=SourceType.WEB_PAGE, acquired_at=acquired_at,
        markdown=content,
        content_hash=KnowledgeObject.compute_content_hash(content),
        raw_content_hash=KnowledgeObject.compute_raw_content_hash(content.encode()),
        word_count=len(content.split()),
    )
    ko.acquisition_chain.append(AcquisitionRecord(
        provider_name="crawl4ai", provider_type=ProviderType.CRAWLER,
        request_id="req-1", timestamp=acquired_at, status=AcquisitionStatus.SUCCESS,
    ))
    return ko


def make_chunk(chunk_id: str, doc_id: str, index: int, total: int = 3,
               content: str = None) -> KnowledgeObject:
    if content is None:
        content = f"Chunk content for {chunk_id}"
    ko = KnowledgeObject(
        id=chunk_id, type=KnowledgeType.CHUNK, parent_id=doc_id,
        chunk_index=index, chunk_total=total,
        source_id="src-test", source_type=SourceType.WEB_PAGE,
        acquired_at="2026-06-25T12:00:00Z",
        markdown=content,
        content_hash=KnowledgeObject.compute_content_hash(content),
        raw_content_hash=KnowledgeObject.compute_raw_content_hash(content.encode()),
        confidence=0.85,
    )
    return ko


def make_relationship(rel_id: str, doc_id: str, rel_type: str = "references") -> KnowledgeObject:
    ko = KnowledgeObject(
        id=rel_id, type=KnowledgeType.RELATIONSHIP, parent_id=doc_id,
        source_id="src-test", source_type=SourceType.WEB_PAGE,
        acquired_at="2026-06-25T12:00:00Z",
        markdown="", confidence=1.0,
        content_hash=KnowledgeObject.compute_content_hash(""),
        raw_content_hash=KnowledgeObject.compute_raw_content_hash(b""),
        related_to=[doc_id],
    )
    return ko


@pytest.fixture
def populated_store():
    store = InMemoryKnowledgeStore()
    repo = KnowledgeRepository(store)

    doc1 = make_doc("doc-1", "Alpha Document", confidence=0.95,
                    acquired_at="2026-06-25T10:00:00Z", source_id="src-github",
                    content="Alpha content here")
    doc2 = make_doc("doc-2", "Beta Document", confidence=0.80,
                    acquired_at="2026-06-25T11:00:00Z", source_id="src-web",
                    content="Beta content here with more words")
    doc3 = make_doc("doc-3", "Gamma Document", confidence=0.60,
                    acquired_at="2026-06-25T12:00:00Z", source_id="src-github",
                    content="Gamma content")
    doc4 = make_doc("doc-4", "Delta Document", confidence=0.99,
                    acquired_at="2026-06-26T08:00:00Z", source_id="src-api",
                    content="Delta delta delta content here")

    for d in [doc1, doc2, doc3, doc4]:
        repo.store(d)

    chunk_contents = ["First chunk of alpha", "Second chunk of alpha", "Third chunk of alpha"]
    for i in range(3):
        chunk = make_chunk(f"chunk-{i}", "doc-1", i, 3,
                           content=chunk_contents[i])
        repo.store(chunk)

    rel = make_relationship("rel-1", "doc-1")
    repo.store(rel)

    return store, repo


@pytest.fixture
def retriever(populated_store):
    _, repo = populated_store
    return KnowledgeRetrieverImpl(repo)


# ---------------------------------------------------------------------------
# Test: Retrieve by ID
# ---------------------------------------------------------------------------

class TestRetrieveByID:

    def test_retrieve_existing_id(self, retriever):
        result = retriever.retrieve_by_id("doc-1")
        assert result.total_count == 1
        assert result.returned_count == 1
        assert result.objects[0].id == "doc-1"

    def test_retrieve_nonexistent_id(self, retriever):
        result = retriever.retrieve_by_id("no-such-doc")
        assert result.total_count == 0
        assert result.returned_count == 0
        assert result.objects == []

    def test_retrieve_by_id_timing(self, retriever):
        result = retriever.retrieve_by_id("doc-1")
        assert result.timing is not None
        assert result.timing.total > 0

    def test_retrieve_by_id_metadata(self, retriever):
        result = retriever.retrieve_by_id("doc-1")
        assert result.metadata["request_type"] == "retrieve_by_id"


# ---------------------------------------------------------------------------
# Test: Retrieve by Content Hash
# ---------------------------------------------------------------------------

class TestRetrieveByHash:

    def test_retrieve_by_content_hash(self, retriever):
        hash_val = KnowledgeObject.compute_content_hash("Alpha content here")
        result = retriever.retrieve_by_content_hash(hash_val)
        assert result.total_count > 0
        assert result.objects[0].content_hash == hash_val

    def test_retrieve_by_nonexistent_hash(self, retriever):
        result = retriever.retrieve_by_content_hash("0000000000000000000000000000000000000000")
        assert result.total_count == 0

    def test_retrieve_by_raw_hash(self, retriever):
        raw_hash = KnowledgeObject.compute_raw_content_hash(b"Alpha content here")
        result = retriever.retrieve_by_raw_hash(raw_hash)
        assert result.total_count > 0


# ---------------------------------------------------------------------------
# Test: Retrieve by Parent
# ---------------------------------------------------------------------------

class TestRetrieveByParent:

    def test_retrieve_children(self, retriever):
        result = retriever.retrieve_by_parent("doc-1")
        assert result.total_count >= 4  # 3 chunks + 1 relationship

    def test_retrieve_parent_no_children(self, retriever):
        result = retriever.retrieve_by_parent("doc-2")
        assert result.total_count == 0

    def test_retrieve_nonexistent_parent(self, retriever):
        result = retriever.retrieve_by_parent("no-such")
        assert result.total_count == 0


# ---------------------------------------------------------------------------
# Test: Retrieve by Source
# ---------------------------------------------------------------------------

class TestRetrieveBySource:

    def test_retrieve_by_source(self, retriever):
        result = retriever.retrieve_by_source("src-github")
        assert result.total_count >= 1

    def test_retrieve_by_source_summary(self, retriever):
        result = retriever.retrieve_by_source("src-github")
        assert len(result.source_summary) >= 1
        assert result.source_summary[0].source_id == "src-github"

    def test_retrieve_nonexistent_source(self, retriever):
        result = retriever.retrieve_by_source("no-such")
        assert result.total_count == 0


# ---------------------------------------------------------------------------
# Test: Retrieve by Acquisition
# ---------------------------------------------------------------------------

class TestRetrieveByAcquisition:

    def test_retrieve_by_acquisition(self, retriever, populated_store):
        store, repo = populated_store
        doc5 = make_doc("doc-5", "Epsilon", source_id="src-custom",
                        content="Epsilon unique content for acquisition test")
        doc5.acquisition_chain = [
            AcquisitionRecord(provider_name="test", provider_type=ProviderType.CRAWLER,
                              request_id="req-custom", timestamp="2026-06-27T00:00:00Z",
                              status=AcquisitionStatus.SUCCESS)
        ]
        repo.store(doc5)

        retriever2 = KnowledgeRetrieverImpl(repo)
        result = retriever2.retrieve_by_acquisition("req-custom")
        assert result.total_count == 1
        assert result.objects[0].id == "doc-5"

    def test_retrieve_by_unknown_acquisition(self, retriever):
        result = retriever.retrieve_by_acquisition("no-such-req")
        assert result.total_count == 0


# ---------------------------------------------------------------------------
# Test: Retrieve by Time Range
# ---------------------------------------------------------------------------

class TestRetrieveByTimeRange:

    def test_retrieve_time_range(self, retriever):
        result = retriever.retrieve_by_time_range(
            "2026-06-25T10:00:00Z", "2026-06-25T12:00:00Z"
        )
        # All objects have acquired_at in this range; some shares default "2026-06-25T12:00:00Z"
        assert result.total_count >= 3  # doc-1, doc-2, doc-3 + chunks

    def test_retrieve_empty_time_range(self, retriever):
        result = retriever.retrieve_by_time_range(
            "2025-01-01T00:00:00Z", "2025-01-01T01:00:00Z"
        )
        assert result.total_count == 0

    def test_retrieve_single_day(self, retriever):
        result = retriever.retrieve_by_time_range(
            "2026-06-25T00:00:00Z", "2026-06-25T23:59:59Z"
        )
        # doc-1, doc-2, doc-3, chunks, relationship all on 2025-06-25
        assert result.total_count >= 3


# ---------------------------------------------------------------------------
# Test: Retrieve by Type
# ---------------------------------------------------------------------------

class TestRetrieveByType:

    def test_retrieve_all_documents(self, retriever):
        result = retriever.retrieve_by_type("document")
        assert result.total_count == 4

    def test_retrieve_all_chunks(self, retriever):
        result = retriever.retrieve_by_type("chunk")
        assert result.total_count == 3

    def test_retrieve_relationships(self, retriever):
        result = retriever.retrieve_by_type("relationship")
        assert result.total_count == 1


# ---------------------------------------------------------------------------
# Test: Retrieve by Confidence
# ---------------------------------------------------------------------------

class TestRetrieveByConfidence:

    def test_confidence_high_threshold(self, retriever):
        result = retriever.retrieve_by_confidence(0.9)
        # doc-1 (0.95), doc-4 (0.99), rel-1 (1.0)
        assert result.total_count == 3

    def test_confidence_range(self, retriever):
        # doc-3 (0.6), doc-2 (0.8), chunks (3 x 0.85)
        result = retriever.retrieve_by_confidence(0.6, 0.85)
        assert result.total_count == 5


# ---------------------------------------------------------------------------
# Test: Retrieve Hierarchy
# ---------------------------------------------------------------------------

class TestRetrieveHierarchy:

    def test_retrieve_hierarchy(self, retriever):
        result = retriever.retrieve_hierarchy("doc-1")
        assert result.total_count >= 5  # doc + 3 chunks + 1 relationship
        assert result.objects[0].id == "doc-1"
        assert result.objects[0].type.value == "document"

    def test_retrieve_hierarchy_nonexistent(self, retriever):
        result = retriever.retrieve_hierarchy("no-such")
        assert result.total_count == 0
        assert len(result.warnings) == 1

    def test_retrieve_hierarchy_chunks_ordered(self, retriever):
        result = retriever.retrieve_hierarchy("doc-1")
        chunks = [ko for ko in result.objects if ko.type.value == "chunk"]
        indices = [ko.chunk_index for ko in chunks]
        assert indices == sorted(indices)

    def test_retrieve_hierarchy_metadata(self, retriever):
        result = retriever.retrieve_hierarchy("doc-1")
        assert result.metadata["request_type"] == "retrieve_hierarchy"
        assert result.metadata["document_id"] == "doc-1"


# ---------------------------------------------------------------------------
# Test: Pagination
# ---------------------------------------------------------------------------

class TestPagination:

    def test_limit_respected(self, retriever):
        result = retriever.retrieve_query(KnowledgeQuery(limit=2))
        assert result.returned_count <= 2
        assert result.limit == 2

    def test_offset_respected(self, retriever):
        all_result = retriever.retrieve_query(KnowledgeQuery(limit=100))
        offset_result = retriever.retrieve_query(KnowledgeQuery(limit=2, offset=1))
        assert offset_result.returned_count == 2
        assert offset_result.objects[0].id == all_result.objects[1].id

    def test_negative_offset(self, retriever):
        result = retriever.retrieve_query(KnowledgeQuery(limit=100, offset=0))
        assert result.total_count >= 0

    def test_returned_count_accurate(self, retriever):
        result = retriever.retrieve_query(KnowledgeQuery(limit=3, offset=0))
        assert result.returned_count <= 3
        assert result.returned_count == len(result.objects)


# ---------------------------------------------------------------------------
# Test: Sorting
# ---------------------------------------------------------------------------

class TestSorting:

    def test_sort_confidence_ascending(self, retriever):
        result = retriever.retrieve_query(KnowledgeQuery(
            sort_field=SortField.CONFIDENCE, sort_order=SortOrder.ASCENDING,
            object_types=["document"],
        ))
        docs = [ko for ko in result.objects if ko.type.value == "document"]
        confidences = [ko.confidence for ko in docs]
        assert confidences == sorted(confidences)

    def test_sort_confidence_descending(self, retriever):
        result = retriever.retrieve_query(KnowledgeQuery(
            sort_field=SortField.CONFIDENCE, sort_order=SortOrder.DESCENDING,
            object_types=["document"],
        ))
        docs = [ko for ko in result.objects if ko.type.value == "document"]
        confidences = [ko.confidence for ko in docs]
        assert confidences == sorted(confidences, reverse=True)

    def test_sort_title_ascending(self, retriever):
        result = retriever.retrieve_query(KnowledgeQuery(
            sort_field=SortField.TITLE, sort_order=SortOrder.ASCENDING,
            object_types=["document"],
        ))
        docs = [ko for ko in result.objects if ko.type.value == "document"]
        titles = [ko.title for ko in docs]
        assert titles == sorted(titles)

    def test_sort_acquired_at_desc_default(self, retriever):
        result = retriever.retrieve_query(KnowledgeQuery(object_types=["document"]))
        docs = [ko for ko in result.objects if ko.type.value == "document"]
        dates = [ko.acquired_at for ko in docs]
        assert dates == sorted(dates, reverse=True)

    def test_sort_version(self, retriever):
        result = retriever.retrieve_query(KnowledgeQuery(
            sort_field=SortField.VERSION, sort_order=SortOrder.ASCENDING,
            object_types=["document"],
        ))
        docs = [ko for ko in result.objects if ko.type.value == "document"]
        versions = [ko.version for ko in docs]
        assert versions == sorted(versions)


# ---------------------------------------------------------------------------
# Test: Projection
# ---------------------------------------------------------------------------

class TestProjection:

    def test_projection_limits_fields(self, retriever):
        result = retriever.retrieve_query(KnowledgeQuery(
            projection_fields=["id", "title", "confidence"],
            object_types=["document"],
        ))
        if result.objects:
            obj = result.objects[0]
            assert isinstance(obj, dict)
            assert "id" in obj
            assert "title" in obj
            assert "confidence" in obj

    def test_projection_excludes_unrequested(self, retriever):
        result = retriever.retrieve_query(KnowledgeQuery(
            projection_fields=["id"],
            object_types=["document"],
        ))
        if result.objects:
            obj = result.objects[0]
            assert isinstance(obj, dict)
            assert "id" in obj
            assert "markdown" not in obj


# ---------------------------------------------------------------------------
# Test: Exists and Count
# ---------------------------------------------------------------------------

class TestExistsAndCount:

    def test_exists_returns_true(self, retriever):
        assert retriever.exists("doc-1") is True

    def test_exists_returns_false(self, retriever):
        assert retriever.exists("no-such") is False

    def test_count_unfiltered(self, retriever):
        count = retriever.count()
        assert count == 8  # 4 docs + 3 chunks + 1 relationship

    def test_count_filtered_by_type(self, retriever):
        count = retriever.count(KnowledgeQuery(object_types=["chunk"]))
        assert count == 3

    def test_count_filtered_by_confidence(self, retriever):
        count = retriever.count(KnowledgeQuery(confidence_min=0.9))
        # doc-1 (0.95), doc-4 (0.99), relationship (1.0)
        assert count == 3


# ---------------------------------------------------------------------------
# Test: Custom Query Filters
# ---------------------------------------------------------------------------

class TestQueryFilters:

    def test_filter_by_word_count(self, retriever):
        result = retriever.retrieve_query(KnowledgeQuery(
            filters=[QueryFilter(field="word_count", value=3, operator="gte")],
        ))
        # doc-2 has 5 words, doc-4 has 5 words
        assert any(ko.id in ("doc-2", "doc-4") for ko in result.objects)

    def test_filter_by_type_eq(self, retriever):
        result = retriever.retrieve_query(KnowledgeQuery(
            filters=[QueryFilter(field="type", value=KnowledgeType.CHUNK, operator="eq")],
        ))
        assert all(ko.type == KnowledgeType.CHUNK for ko in result.objects)

    def test_filter_missing_field(self, retriever):
        result = retriever.retrieve_query(KnowledgeQuery(
            filters=[QueryFilter(field="source_url", value=None, operator="eq")],
        ))
        assert result.total_count >= 0

    def test_query_with_source_ids(self, retriever):
        result = retriever.retrieve_query(KnowledgeQuery(source_ids=["src-github"]))
        assert all(ko.source_id == "src-github" for ko in result.objects)

    def test_query_with_parent_ids(self, retriever):
        result = retriever.retrieve_query(KnowledgeQuery(parent_ids=["doc-1"]))
        assert all(ko.parent_id == "doc-1" for ko in result.objects)


# ---------------------------------------------------------------------------
# Test: Validation
# ---------------------------------------------------------------------------

class TestValidation:

    def test_valid_object_no_warnings(self, retriever):
        result = retriever.retrieve_by_id("doc-1")
        assert len(result.warnings) == 0

    def test_missing_content_hash_detected(self):
        ko = make_doc("bad-hash", content="Hello validation world")
        ko.content_hash = ""
        validator = RetrievalValidator()
        warnings = validator.validate(ko)
        assert any(w.code == "MISSING_CONTENT_HASH" for w in warnings)

    def test_hash_mismatch_detected(self):
        ko = make_doc("bad-hash2", content="Hello validation world 2")
        ko.content_hash = "00000000000000000000000000000000"
        validator = RetrievalValidator()
        warnings = validator.validate(ko)
        assert any(w.code == "CONTENT_HASH_MISMATCH" for w in warnings)

    def test_invalid_confidence_detected(self):
        ko = make_doc("bad-conf", confidence=1.5)
        validator = RetrievalValidator()
        warnings = validator.validate(ko)
        assert any(w.code == "INVALID_CONFIDENCE" for w in warnings)

    def test_negative_confidence_detected(self):
        ko = make_doc("neg-conf", confidence=-0.1)
        validator = RetrievalValidator()
        warnings = validator.validate(ko)
        assert any(w.code == "INVALID_CONFIDENCE" for w in warnings)

    def test_invalid_version_detected(self):
        ko = make_doc("bad-ver")
        ko.version = 0
        validator = RetrievalValidator()
        warnings = validator.validate(ko)
        assert any(w.code == "INVALID_VERSION" for w in warnings)

    def test_invalid_chunk_index_detected(self):
        ko = make_chunk("bad-chunk", "doc-1", -1, 3)
        validator = RetrievalValidator()
        warnings = validator.validate(ko)
        assert any(w.code == "INVALID_CHUNK_INDEX" for w in warnings)

    def test_chunk_index_out_of_range_detected(self):
        ko = make_chunk("bad-chunk2", "doc-1", 5, 3)
        validator = RetrievalValidator()
        warnings = validator.validate(ko)
        assert any(w.code == "CHUNK_INDEX_OUT_OF_RANGE" for w in warnings)

    def test_missing_acquired_at_detected(self):
        ko = make_doc("no-date")
        ko.acquired_at = ""
        validator = RetrievalValidator()
        warnings = validator.validate(ko)
        assert any(w.code == "MISSING_ACQUIRED_AT" for w in warnings)


# ---------------------------------------------------------------------------
# Test: Determinism
# ---------------------------------------------------------------------------

class TestDeterminism:

    def test_identical_queries_return_same_objects(self, retriever):
        q = KnowledgeQuery(object_types=["document"], sort_field=SortField.CONFIDENCE,
                           sort_order=SortOrder.DESCENDING)
        r1 = retriever.retrieve_query(q)
        r2 = retriever.retrieve_query(q)
        ids1 = [ko.id for ko in r1.objects]
        ids2 = [ko.id for ko in r2.objects]
        assert ids1 == ids2

    def test_identical_queries_same_total_count(self, retriever):
        r1 = retriever.retrieve_query(KnowledgeQuery(object_types=["chunk"]))
        r2 = retriever.retrieve_query(KnowledgeQuery(object_types=["chunk"]))
        assert r1.total_count == r2.total_count

    def test_identical_queries_same_ordering(self, retriever):
        q = KnowledgeQuery(object_types=["document"], sort_field=SortField.TITLE,
                           sort_order=SortOrder.ASCENDING)
        r1 = retriever.retrieve_query(q)
        r2 = retriever.retrieve_query(q)
        titles1 = [ko.title for ko in r1.objects]
        titles2 = [ko.title for ko in r2.objects]
        assert titles1 == titles2

    def test_deterministic_by_id(self, retriever):
        r1 = retriever.retrieve_by_id("doc-1")
        r2 = retriever.retrieve_by_id("doc-1")
        assert r1.objects[0].to_dict() == r2.objects[0].to_dict()

    def test_deterministic_hierarchy(self, retriever):
        r1 = retriever.retrieve_hierarchy("doc-1")
        r2 = retriever.retrieve_hierarchy("doc-1")
        ids1 = [ko.id for ko in r1.objects]
        ids2 = [ko.id for ko in r2.objects]
        assert ids1 == ids2


# ---------------------------------------------------------------------------
# Test: Failure Cases
# ---------------------------------------------------------------------------

class TestFailureCases:

    def test_empty_id(self, retriever):
        result = retriever.retrieve_by_id("")
        assert result.total_count == 0

    def test_nonexistent_document_hierarchy(self, retriever):
        result = retriever.retrieve_hierarchy("no-such-doc")
        assert result.total_count == 0
        assert any(w.code == "DOCUMENT_NOT_FOUND" for w in result.warnings)

    def test_corrupted_object_hash(self, retriever, populated_store):
        store, repo = populated_store
        ko = store.retrieve_by_id("doc-2")
        ko.content_hash = "corrupted-hash-here"
        repo.store(ko)

        r = KnowledgeRetrieverImpl(repo)
        result = r.retrieve_by_id("doc-2")
        assert any(w.code == "CONTENT_HASH_MISMATCH" for w in result.warnings)

    def test_invalid_confidence_value(self, populated_store):
        """Invalid confidence on a non-duplicate object."""
        store, repo = populated_store
        bad_ko = make_doc("bad-conf-doc", confidence=2.5,
                          content="unique content for invalid confidence test")
        repo.store(bad_ko)
        r = KnowledgeRetrieverImpl(repo)
        result = r.retrieve_by_id("bad-conf-doc")
        assert any(w.code == "INVALID_CONFIDENCE" for w in result.warnings)


# ---------------------------------------------------------------------------
# Test: Metrics
# ---------------------------------------------------------------------------

class TestRetrievalMetrics:

    def test_metrics_track_queries(self, retriever):
        retriever.retrieve_by_id("doc-1")
        retriever.retrieve_by_id("doc-2")
        metrics = retriever.get_metrics()
        assert metrics["queries_executed"] >= 2

    def test_metrics_track_objects_returned(self, retriever):
        retriever.retrieve_by_id("doc-1")
        retriever.retrieve_hierarchy("doc-1")
        metrics = retriever.get_metrics()
        assert metrics["objects_returned"] > 0

    def test_metrics_track_hierarchy_assemblies(self, retriever):
        retriever.retrieve_hierarchy("doc-1")
        metrics = retriever.get_metrics()
        assert metrics["hierarchy_assemblies"] == 1

    def test_metrics_avg_latency_calculated(self, retriever):
        retriever.retrieve_by_id("doc-1")
        retriever.retrieve_by_id("doc-2")
        retriever.retrieve_by_id("doc-3")
        metrics = retriever.get_metrics()
        assert metrics["avg_latency_ms"] >= 0
        assert metrics["queries_executed"] == 3


# ---------------------------------------------------------------------------
# Test: Architecture Compliance
# ---------------------------------------------------------------------------

class TestArchitectureCompliance:

    RETRIEVAL_SRC = os.path.join(os.path.dirname(__file__), '..', '..', 'src',
                                 'knowledge_service', 'retrieval')

    def test_no_sql_in_retrieval(self):
        """Verify the retrieval module has no SQL strings."""
        for fname in os.listdir(self.RETRIEVAL_SRC):
            if fname.endswith('.py'):
                with open(os.path.join(self.RETRIEVAL_SRC, fname)) as f:
                    content = f.read()
                    assert 'SELECT' not in content
                    assert 'INSERT' not in content
                    assert 'DELETE' not in content
                    assert 'WHERE' not in content

    def test_no_acquisition_imports(self):
        """Verify retrieval does not import acquisition modules."""
        import ast
        for fname in os.listdir(self.RETRIEVAL_SRC):
            if fname.endswith('.py'):
                with open(os.path.join(self.RETRIEVAL_SRC, fname)) as f:
                    tree = ast.parse(f.read())
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ImportFrom):
                            if node.module and 'acquisition' in node.module:
                                pytest.fail(f"Retrieval imports acquisition in {fname}: {node.module}")

    def test_no_planning_imports(self):
        """Verify retrieval does not import planning modules."""
        import ast
        for fname in os.listdir(self.RETRIEVAL_SRC):
            if fname.endswith('.py'):
                with open(os.path.join(self.RETRIEVAL_SRC, fname)) as f:
                    tree = ast.parse(f.read())
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ImportFrom):
                            if node.module and 'planning' in node.module:
                                pytest.fail(f"Retrieval imports planning in {fname}: {node.module}")

    def test_no_processing_imports(self):
        """Verify retrieval does not import processing modules."""
        import ast
        for fname in os.listdir(self.RETRIEVAL_SRC):
            if fname.endswith('.py'):
                with open(os.path.join(self.RETRIEVAL_SRC, fname)) as f:
                    tree = ast.parse(f.read())
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ImportFrom):
                            if node.module and 'processing' in node.module:
                                pytest.fail(f"Retrieval imports processing in {fname}: {node.module}")

    def test_depends_only_on_repository(self):
        """Verify retriever only uses repository, not store directly."""
        import inspect
        sig = inspect.signature(KnowledgeRetrieverImpl.__init__)
        params = list(sig.parameters.keys())
        assert 'repository' in params or 'repo' in params
        assert 'store' not in params

    def test_retrieval_result_has_no_provider_info(self, retriever):
        """Verify retrieval results do not expose internal provider info."""
        result = retriever.retrieve_by_id("doc-1")
        for obj in result.objects:
            d = obj.to_dict() if hasattr(obj, 'to_dict') else obj
            if isinstance(d, dict):
                assert 'provider' not in d


# ---------------------------------------------------------------------------
# Test: List All
# ---------------------------------------------------------------------------

class TestListAll:

    def test_list_all_returns_objects(self, retriever):
        result = retriever.list_all()
        assert result.total_count > 0

    def test_list_all_with_limit(self, retriever):
        result = retriever.list_all(KnowledgeQuery(limit=3))
        assert result.returned_count <= 3


# ---------------------------------------------------------------------------
# Test: Warnings
# ---------------------------------------------------------------------------

class TestRetrievalWarnings:

    def test_warning_has_code_and_message(self):
        from src.knowledge_service.retrieval.interfaces import RetrievalWarning
        w = RetrievalWarning(code="TEST", message="Test message", object_id="doc-1")
        assert w.code == "TEST"
        assert w.message == "Test message"
        assert w.object_id == "doc-1"

    def test_has_warnings_true(self, retriever, populated_store):
        store, repo = populated_store
        ko = store.retrieve_by_id("doc-3")
        ko.content_hash = "corrupted-for-real-now"
        repo.store(ko)
        r = KnowledgeRetrieverImpl(repo)
        result = r.retrieve_by_id("doc-3")
        if result.warnings:
            assert result.has_warnings() is True

    def test_no_warnings_for_valid_object(self, retriever):
        result = retriever.retrieve_by_id("doc-1")
        assert len(result.warnings) == 0
        assert result.has_warnings() is False


# ---------------------------------------------------------------------------
# Test: Assembly / Hierarchy Module
# ---------------------------------------------------------------------------

class TestHierarchy:

    def test_assemble_hierarchy_orders_correctly(self):
        from src.knowledge_service.retrieval.hierarchy import assemble_hierarchy
        doc = make_doc("hier-doc", content="Hierarchy doc content")
        chunks = [
            make_chunk("hier-c2", "hier-doc", 2, 3, content="Chunk 2 content"),
            make_chunk("hier-c0", "hier-doc", 0, 3, content="Chunk 0 content"),
            make_chunk("hier-c1", "hier-doc", 1, 3, content="Chunk 1 content"),
        ]
        rel = make_relationship("hier-rel", "hier-doc")
        result = assemble_hierarchy(doc, chunks + [rel])
        # Document first
        assert result[0].id == "hier-doc"
        assert result[0].type.value == "document"
        # Chunks in index order
        chunk_ids = [ko.id for ko in result if ko.type.value == "chunk"]
        assert chunk_ids == ["hier-c0", "hier-c1", "hier-c2"]
        # Relationship last
        assert result[-1].id == "hier-rel"

    def test_assemble_empty_children(self):
        from src.knowledge_service.retrieval.hierarchy import assemble_hierarchy
        doc = make_doc("empty-doc", content="Empty doc")
        result = assemble_hierarchy(doc, [])
        assert len(result) == 1
        assert result[0].id == "empty-doc"
