"""PostgreSQL Knowledge Store — PostgreSQL implementation of the KnowledgeStore interface

Uses psycopg2 to interact with PostgreSQL. No SQL escapes this module; all queries are parameterized.
"""

import psycopg2
from psycopg2 import errors as pg_errors
from typing import Optional, List, Dict, Any
import json
from datetime import datetime, timezone
from ...knowledge_object import KnowledgeObject, KnowledgeType, SourceType, IndexStatus
from ..interfaces.store import KnowledgeStore
from ..interfaces.source_store import SourceStore
from ..repositories.source_entry import SourceEntry


class PostgreSQLKnowledgeStore(KnowledgeStore):
    """PostgreSQL implementation of the KnowledgeStore interface."""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self._conn = None
        self._metrics = {
            "objects_stored": 0,
            "objects_retrieved": 0,
            "duplicates_prevented": 0,
            "write_latencies_ms": [],
            "read_latencies_ms": []
        }

    def _get_connection(self):
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(self.connection_string)
        return self._conn

    def _ensure_tables_exist(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            # Create knowledge_objects table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_objects (
                    id UUID PRIMARY KEY,
                    version INTEGER NOT NULL DEFAULT 1,
                    type VARCHAR(50) NOT NULL,
                    source_id VARCHAR(255) NOT NULL,
                    source_url TEXT,
                    source_type VARCHAR(50) NOT NULL,
                    acquired_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    published_at TIMESTAMP WITH TIME ZONE,
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    markdown TEXT,
                    structured_data JSONB,
                    raw_content_hash CHAR(64) NOT NULL,
                    content_hash CHAR(64) NOT NULL UNIQUE,
                    title VARCHAR(500),
                    authors TEXT[],
                    language VARCHAR(10),
                    topics TEXT[],
                    word_count INTEGER,
                    confidence FLOAT NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
                    evidence_count INTEGER NOT NULL,
                    citations JSONB,
                    acquisition_chain JSONB,
                    parent_id UUID,
                    chunk_index INTEGER,
                    chunk_total INTEGER,
                    overlap_with_next_id UUID,
                    related_to UUID[],
                    relationship_types TEXT[],
                    storage_backend VARCHAR(100) NOT NULL,
                    index_status VARCHAR(20) NOT NULL,
                    retention_policy_id VARCHAR(100),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at_storage TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_ko_source_id ON knowledge_objects(source_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_ko_acquired_at ON knowledge_objects(acquired_at)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_ko_content_hash ON knowledge_objects(content_hash)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_ko_raw_content_hash ON knowledge_objects(raw_content_hash)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_ko_parent_id ON knowledge_objects(parent_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_ko_type ON knowledge_objects(type)
            """)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def store(self, ko: KnowledgeObject) -> str:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            ko_data = ko.to_dict()
            # Check for duplicate by content_hash
            cursor.execute("SELECT id FROM knowledge_objects WHERE content_hash = %s", (ko.content_hash,))
            existing = cursor.fetchone()
            if existing:
                self._metrics["duplicates_prevented"] += 1
                return existing[0]

            # Insert or update
            cursor.execute("""
                INSERT INTO knowledge_objects (
                    id, version, type, source_id, source_url, source_type, acquired_at, published_at,
                    updated_at, markdown, structured_data, raw_content_hash, content_hash, title,
                    authors, language, topics, word_count, confidence, evidence_count, citations,
                    acquisition_chain, parent_id, chunk_index, chunk_total, overlap_with_next_id,
                    related_to, relationship_types, storage_backend, index_status, retention_policy_id
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (content_hash) DO NOTHING
                RETURNING id
            """, (
                ko.id, ko.version, ko.type.value, ko.source_id, ko.source_url, ko.source_type.value,
                ko.acquired_at, ko.published_at, ko.updated_at, ko.markdown,
                json.dumps(ko.structured_data) if ko.structured_data else None,
                ko.raw_content_hash, ko.content_hash, ko.title,
                ','.join(ko.authors) if ko.authors else None, ko.language,
                ','.join(ko.topics) if ko.topics else None, ko.word_count, ko.confidence,
                ko.evidence_count, json.dumps(ko_data.get("citations")) if ko.citations else None,
                json.dumps(ko_data.get("acquisition_chain")) if ko.acquisition_chain else None,
                ko.parent_id, ko.chunk_index, ko.chunk_total, ko.overlap_with_next_id,
                ko.related_to, [rt.value for rt in ko.relationship_types] if ko.relationship_types else None,
                ko.storage_backend, ko.index_status.value, ko.retention_policy_id
            ))
            row = cursor.fetchone()
            if row:
                stored_id = row[0]
            else:
                # Already existed due to content_hash conflict, retrieve it
                cursor.execute("SELECT id FROM knowledge_objects WHERE content_hash = %s", (ko.content_hash,))
                stored_id = cursor.fetchone()[0]

            conn.commit()
            self._metrics["objects_stored"] += 1
            return stored_id
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def retrieve_by_id(self, obj_id: str) -> Optional[KnowledgeObject]:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM knowledge_objects WHERE id = %s", (obj_id,))
            row = cursor.fetchone()
            if not row:
                return None
            self._metrics["objects_retrieved"] += 1
            return self._row_to_ko(row)
        finally:
            cursor.close()

    def retrieve_by_hash(self, content_hash: str) -> Optional[KnowledgeObject]:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM knowledge_objects WHERE content_hash = %s", (content_hash,))
            row = cursor.fetchone()
            if not row:
                return None
            self._metrics["objects_retrieved"] += 1
            return self._row_to_ko(row)
        finally:
            cursor.close()

    def retrieve_by_raw_hash(self, raw_content_hash: str) -> Optional[KnowledgeObject]:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM knowledge_objects WHERE raw_content_hash = %s", (raw_content_hash,))
            row = cursor.fetchone()
            if not row:
                return None
            self._metrics["objects_retrieved"] += 1
            return self._row_to_ko(row)
        finally:
            cursor.close()

    def retrieve_by_parent(self, parent_id: str) -> List[KnowledgeObject]:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM knowledge_objects WHERE parent_id = %s", (parent_id,))
            rows = cursor.fetchall()
            self._metrics["objects_retrieved"] += len(rows)
            return [self._row_to_ko(row) for row in rows]
        finally:
            cursor.close()

    def list_by_source(self, source_id: str, limit: int = 100, offset: int = 0) -> List[KnowledgeObject]:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT * FROM knowledge_objects WHERE source_id = %s ORDER BY acquired_at DESC LIMIT %s OFFSET %s",
                (source_id, limit, offset)
            )
            rows = cursor.fetchall()
            self._metrics["objects_retrieved"] += len(rows)
            return [self._row_to_ko(row) for row in rows]
        finally:
            cursor.close()

    def list_by_date_range(self, start_date: str, end_date: str, limit: int = 100) -> List[KnowledgeObject]:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT * FROM knowledge_objects WHERE acquired_at BETWEEN %s AND %s ORDER BY acquired_at DESC LIMIT %s",
                (start_date, end_date, limit)
            )
            rows = cursor.fetchall()
            self._metrics["objects_retrieved"] += len(rows)
            return [self._row_to_ko(row) for row in rows]
        finally:
            cursor.close()

    def delete(self, obj_id: str) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM knowledge_objects WHERE id = %s RETURNING id", (obj_id,))
            row = cursor.fetchone()
            conn.commit()
            if row:
                return True
            return False
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def check_duplicate(self, content_hash: str) -> Optional[str]:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id FROM knowledge_objects WHERE content_hash = %s", (content_hash,))
            row = cursor.fetchone()
            if row:
                return row[0]
            return None
        finally:
            cursor.close()

    def get_metrics(self) -> Dict[str, Any]:
        return self._metrics.copy()

    def health(self) -> bool:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            return True
        except Exception:
            return False

    def _row_to_ko(self, row) -> KnowledgeObject:
        # Row columns: id, version, type, source_id, source_url, source_type, acquired_at, published_at,
        # updated_at, markdown, structured_data, raw_content_hash, content_hash, title, authors, language,
        # topics, word_count, confidence, evidence_count, citations, acquisition_chain, parent_id,
        # chunk_index, chunk_total, overlap_with_next_id, related_to, relationship_types, storage_backend,
        # index_status, retention_policy_id, created_at, updated_at_storage
        authors = row[14] if isinstance(row[14], list) else (row[14].split(',') if row[14] else [])
        topics = row[16] if isinstance(row[16], list) else (row[16].split(',') if row[16] else [])
        related_to = row[26] or []
        rel_types_strs = row[27] or []
        data = {
            "id": str(row[0]),
            "version": row[1],
            "type": row[2],
            "source_id": row[3],
            "source_url": row[4],
            "source_type": row[5],
            "acquired_at": str(row[6]),
            "published_at": str(row[7]) if row[7] else None,
            "updated_at": str(row[8]),
            "markdown": row[9],
            "structured_data": row[10] if isinstance(row[10], dict) else (json.loads(row[10]) if row[10] else None),
            "raw_content_hash": row[11],
            "content_hash": row[12],
            "title": row[13],
            "authors": authors,
            "language": row[15],
            "topics": topics,
            "word_count": row[17],
            "confidence": row[18],
            "evidence_count": row[19],
            "citations": row[20] if isinstance(row[20], list) else (json.loads(row[20]) if row[20] else []),
            "acquisition_chain": row[21] if isinstance(row[21], list) else (json.loads(row[21]) if row[21] else []),
            "parent_id": str(row[22]) if row[22] else None,
            "chunk_index": row[23],
            "chunk_total": row[24],
            "overlap_with_next_id": str(row[25]) if row[25] else None,
            "related_to": related_to,
            "relationship_types": rel_types_strs,
            "storage_backend": row[28],
            "index_status": row[29],
            "retention_policy_id": row[30],
        }
        return KnowledgeObject.from_dict(data)


class PostgreSQLSourceStore(SourceStore):
    """PostgreSQL implementation of the SourceStore interface."""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self._conn = None
        self._metrics = {
            "sources_registered": 0,
            "metrics_updated": 0,
            "searches_run": 0,
            "list_requests": 0,
        }

    def _get_connection(self):
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(self.connection_string)
        return self._conn

    def _ensure_tables_exist(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS source_registry (
                    id VARCHAR(255) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    url TEXT,
                    type VARCHAR(50) NOT NULL,
                    trust_score REAL NOT NULL DEFAULT 0.5,
                    freshness_score REAL NOT NULL DEFAULT 1.0,
                    avg_latency_ms INTEGER NOT NULL DEFAULT 0,
                    success_rate REAL NOT NULL DEFAULT 1.0,
                    topics TEXT[],
                    cache_policy JSONB,
                    status VARCHAR(20) NOT NULL DEFAULT 'healthy',
                    last_acquired_at TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    topic_scores JSONB NOT NULL DEFAULT '{}'::JSONB
                )
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sr_status ON source_registry(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sr_topics ON source_registry USING GIN(topics)")
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def register_source(self, source: SourceEntry) -> bool:
        self._ensure_tables_exist()
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO source_registry (
                    id, name, url, type, trust_score, freshness_score, avg_latency_ms,
                    success_rate, topics, cache_policy, status, last_acquired_at,
                    created_at, updated_at, topic_scores
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                RETURNING id
                """,
                (
                    source.id,
                    source.name,
                    source.url,
                    source.type,
                    source.trust_score,
                    source.freshness_score,
                    source.avg_latency_ms,
                    source.success_rate,
                    source.topics,
                    json.dumps(source.cache_policy),
                    source.status,
                    source.last_acquired_at,
                    source.created_at,
                    source.updated_at,
                    json.dumps(source.topic_scores or {}),
                ),
            )
            row = cursor.fetchone()
            conn.commit()
            if row is None:
                return False
            self._metrics["sources_registered"] += 1
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def get_source(self, source_id: str) -> Optional[SourceEntry]:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM source_registry WHERE id = %s", (source_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_source_entry(row)
        finally:
            cursor.close()

    def update_source_metrics(self, source_id: str, trust_score: Optional[float] = None,
                             freshness_score: Optional[float] = None, avg_latency_ms: Optional[int] = None,
                             success_rate: Optional[float] = None, last_acquired_at: Optional[str] = None,
                             status: Optional[str] = None):
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM source_registry WHERE id = %s", (source_id,))
            if not cursor.fetchone():
                return False

            fields = []
            params: List[Any] = []
            if trust_score is not None:
                fields.append("trust_score = %s")
                params.append(trust_score)
            if freshness_score is not None:
                fields.append("freshness_score = %s")
                params.append(freshness_score)
            if avg_latency_ms is not None:
                fields.append("avg_latency_ms = %s")
                params.append(avg_latency_ms)
            if success_rate is not None:
                fields.append("success_rate = %s")
                params.append(success_rate)
            if last_acquired_at is not None:
                fields.append("last_acquired_at = %s")
                params.append(last_acquired_at)
            if status is not None:
                fields.append("status = %s")
                params.append(status)

            fields.append("updated_at = %s")
            params.append(datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))

            if not fields:
                return False

            params.append(source_id)
            cursor.execute(
                f"UPDATE source_registry SET {', '.join(fields)} WHERE id = %s",
                tuple(params)
            )
            conn.commit()
            self._metrics["metrics_updated"] += 1
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def list_sources(self, status: Optional[str] = None, limit: int = 100) -> List[SourceEntry]:
        self._ensure_tables_exist()
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            self._metrics["list_requests"] += 1
            params: List[Any] = []
            if status:
                query = "SELECT * FROM source_registry WHERE status = %s ORDER BY updated_at DESC LIMIT %s"
                params = [status.lower(), limit]
            else:
                query = "SELECT * FROM source_registry ORDER BY updated_at DESC LIMIT %s"
                params = [limit]

            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            return [self._row_to_source_entry(row) for row in rows]
        finally:
            cursor.close()

    def search_by_topic(self, topic: str, min_confidence: float = 0.3) -> List[SourceEntry]:
        self._ensure_tables_exist()
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            self._metrics["searches_run"] += 1
            query = "SELECT * FROM source_registry ORDER BY updated_at DESC"
            cursor.execute(query)
            rows = cursor.fetchall()
            result = []
            normalized_topic = topic.strip().lower()
            for row in rows:
                source = self._row_to_source_entry(row)
                confidence = source.topic_scores.get(normalized_topic, 0.0)
                if normalized_topic not in source.topic_scores and normalized_topic in [t.lower() for t in source.topics]:
                    confidence = 1.0
                if confidence >= min_confidence:
                    result.append(source)
            return result
        finally:
            cursor.close()

    def get_metrics(self) -> Dict[str, Any]:
        return self._metrics.copy()

    def health(self) -> bool:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            return True
        except Exception:
            return False

    def _row_to_source_entry(self, row) -> SourceEntry:
        # Row columns: id, name, url, type, trust_score, freshness_score, avg_latency_ms,
        # success_rate, topics, cache_policy, status, last_acquired_at, created_at,
        # updated_at, topic_scores
        topics = row[8] or []
        cache_policy = json.loads(row[9]) if isinstance(row[9], str) else (row[9] or {})
        topic_scores = row[14] if isinstance(row[14], dict) else json.loads(row[14]) if row[14] else {}

        return SourceEntry(
            id=row[0],
            name=row[1],
            url=row[2],
            type=row[3],
            trust_score=row[4],
            freshness_score=row[5],
            avg_latency_ms=row[6],
            success_rate=row[7],
            topics=list(topics),
            cache_policy=cache_policy,
            status=row[10],
            last_acquired_at=str(row[11]) if row[11] else None,
            created_at=str(row[12]),
            updated_at=str(row[13]),
            topic_scores={k: float(v) for k, v in (topic_scores or {}).items()},
        )
