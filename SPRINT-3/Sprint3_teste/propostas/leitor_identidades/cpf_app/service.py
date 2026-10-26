"""Casos de uso locais. Identidade do chamador é simulada, não autenticada."""
from hashlib import sha256
from pathlib import Path
from .domain import RULE_VERSION, RuleError, require
from .extraction import Extractor
from .storage import Store


class Workflow:
    def __init__(self, store: Store, extractor: Extractor):
        self.store, self.extractor = store, extractor

    def ingest(self, path, actor):
        require(actor, actor.unit, write=True)
        path = Path(path)
        with path.open('rb') as source:
            content = source.read(5_000_001)
        if len(content) > 5_000_000:
            raise RuleError('Arquivo acima de 5 MB')
        digest = sha256(content).hexdigest()
        result = self.extractor.extract(content, path.suffix.lower())
        state = 'OCR_REQUIRED' if result.requires_ocr else ('REVIEW' if result.candidates else 'NO_CPF')
        db = self.store.db
        self.store.begin()
        try:
            row = db.execute('SELECT id FROM document WHERE unit=? AND digest=? AND extractor=? AND rules=?',
                             (actor.unit, digest, self.extractor.version, RULE_VERSION)).fetchone()
            if row:
                db.commit()
                return row['id']
            doc_id = db.execute('INSERT INTO document(unit,digest,source,extractor,rules,state) VALUES (?,?,?,?,?,?)',
                                (actor.unit, digest, content, self.extractor.version, RULE_VERSION, state)).lastrowid
            for c in result.candidates:
                db.execute('INSERT INTO candidate(document_id,cpf,page,start,end,evidence,consistent) VALUES (?,?,?,?,?,?,?)',
                           (doc_id, c.cpf, c.page, c.start, c.end, c.evidence, int(c.consistent)))
            self.store.event(doc_id, 'IMPORTED', actor, state)
            db.commit()
            return doc_id
        except Exception:
            db.rollback()
            raise

    def inspect(self, doc_id, actor):
        db = self.store.db
        doc = db.execute('SELECT id,unit,digest,extractor,rules,state,version FROM document WHERE id=?', (doc_id,)).fetchone()
        if doc is None:
            raise RuleError('Documento não encontrado')
        require(actor, doc['unit'])
        candidates = []
        for row in db.execute('SELECT * FROM candidate WHERE document_id=? ORDER BY id', (doc_id,)):
            item = dict(row)
            item['possible_credits'] = [dict(r) for r in db.execute('SELECT id,description FROM credit WHERE unit=? AND cpf=?', (doc['unit'], row['cpf']))]
            candidates.append(item)
        return {'document': dict(doc), 'candidates': candidates,
                'audit': [dict(r) for r in db.execute('SELECT * FROM audit WHERE document_id=? ORDER BY id', (doc_id,))]}

    def decide(self, doc_id, actor, expected_version, approve, reason, candidate_id=None, credit_id=None, subject_confirmed=False):
        if not reason or not reason.strip():
            raise RuleError('Justificativa obrigatória')
        if len(reason) > 1000:
            raise RuleError('Justificativa acima de 1000 caracteres')
        db = self.store.db
        self.store.begin()
        try:
            doc = db.execute('SELECT * FROM document WHERE id=?', (doc_id,)).fetchone()
            if doc is None:
                raise RuleError('Documento não encontrado')
            require(actor, doc['unit'], write=True)
            if doc['version'] != expected_version or doc['state'] in ('APPROVED', 'REJECTED'):
                raise RuleError('Decisão desatualizada ou documento já encerrado')
            if approve:
                if doc['state'] != 'REVIEW' or not subject_confirmed:
                    raise RuleError('Conferência do sujeito e extração completa são obrigatórias')
                candidate = db.execute('SELECT * FROM candidate WHERE id=? AND document_id=?', (candidate_id, doc_id)).fetchone()
                credit = db.execute('SELECT * FROM credit WHERE id=? AND unit=?', (credit_id, doc['unit'])).fetchone()
                if not candidate or not candidate['consistent'] or not credit or candidate['cpf'] != credit['cpf']:
                    raise RuleError('Candidato inconsistente ou incompatível com crédito/unidade')
                db.execute('INSERT INTO link VALUES (?,?,?,?,?)', (doc_id, candidate_id, credit_id, actor.name, reason))
            state = 'APPROVED' if approve else 'REJECTED'
            db.execute('UPDATE document SET state=?, version=version+1 WHERE id=?', (state, doc_id))
            self.store.event(doc_id, state, actor, reason)
            db.commit()
        except Exception:
            db.rollback()
            raise
