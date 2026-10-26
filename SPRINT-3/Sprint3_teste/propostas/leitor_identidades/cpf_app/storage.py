"""Adaptador SQLite: documento e eventos são gravados na mesma transação."""
import sqlite3

SCHEMA = '''
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS document (
 id INTEGER PRIMARY KEY, unit TEXT NOT NULL, digest TEXT NOT NULL, source BLOB NOT NULL,
 extractor TEXT NOT NULL, rules TEXT NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('REVIEW','OCR_REQUIRED','NO_CPF','APPROVED','REJECTED')),
 version INTEGER NOT NULL DEFAULT 1,
 UNIQUE(unit,digest,extractor,rules)
);
CREATE TABLE IF NOT EXISTS candidate (
 id INTEGER PRIMARY KEY, document_id INTEGER NOT NULL REFERENCES document(id), cpf TEXT NOT NULL,
 page INTEGER NOT NULL, start INTEGER NOT NULL, end INTEGER NOT NULL, evidence TEXT NOT NULL,
 consistent INTEGER NOT NULL CHECK(consistent IN (0,1))
);
CREATE TABLE IF NOT EXISTS credit (
 id TEXT PRIMARY KEY, unit TEXT NOT NULL, cpf TEXT NOT NULL, description TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS link (
 document_id INTEGER PRIMARY KEY REFERENCES document(id), candidate_id INTEGER NOT NULL REFERENCES candidate(id),
 credit_id TEXT NOT NULL REFERENCES credit(id), reviewer TEXT NOT NULL, reason TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit (
 id INTEGER PRIMARY KEY, document_id INTEGER NOT NULL REFERENCES document(id),
 event TEXT NOT NULL, actor TEXT NOT NULL, details TEXT NOT NULL,
 created TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE TRIGGER IF NOT EXISTS no_audit_update BEFORE UPDATE ON audit
BEGIN SELECT RAISE(ABORT,'Eventos de auditoria não podem ser alterados'); END;
CREATE TRIGGER IF NOT EXISTS no_audit_delete BEFORE DELETE ON audit
BEGIN SELECT RAISE(ABORT,'Eventos de auditoria não podem ser excluídos'); END;
'''


class Store:
    def __init__(self, path):
        self.db = sqlite3.connect(path, isolation_level=None, timeout=10)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

    def close(self):
        self.db.close()

    def begin(self):
        self.db.execute('BEGIN IMMEDIATE')

    def event(self, document, event, actor, details):
        self.db.execute('INSERT INTO audit(document_id,event,actor,details) VALUES (?,?,?,?)',
                        (document, event, actor.name, details))
