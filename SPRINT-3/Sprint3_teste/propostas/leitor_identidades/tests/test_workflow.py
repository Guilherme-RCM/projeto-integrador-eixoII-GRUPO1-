import sqlite3
import tempfile
import unittest
from pathlib import Path
from pypdf import PdfWriter
from cpf_app.domain import Actor, RuleError, valid_cpf
from cpf_app.extraction import LocalTextExtractor
from cpf_app.storage import Store
from cpf_app.service import Workflow


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = Store(self.root / 'test.sqlite')
        self.flow = Workflow(self.store, LocalTextExtractor())
        self.actor = Actor('Ana fictícia', 'reviewer', 'A')
        self.other = Actor('Beto fictício', 'reviewer', 'B')
        self.store.db.executemany('INSERT INTO credit VALUES (?,?,?,?)', [
            ('a1', 'A', '00000000191', 'Fictício A'), ('b1', 'B', '00000000191', 'Fictício B'),
            ('a2', 'A', '12345678909', 'Outro cadastro fictício')])

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def ingest(self, text='Contribuinte: CPF 000.000.001-91', name='input.txt'):
        path = self.root / name
        path.write_text(text, encoding='utf-8')
        return self.flow.ingest(path, self.actor)

    def approve(self, doc, **changes):
        values = dict(doc_id=doc, actor=self.actor, expected_version=1, approve=True,
                      reason='Conferidos documento e crédito fictícios',
                      candidate_id=self.flow.inspect(doc, self.actor)['candidates'][0]['id'],
                      credit_id='a1', subject_confirmed=True)
        values.update(changes)
        self.flow.decide(**values)

    def test_checksum_is_only_consistency(self):
        self.assertTrue(valid_cpf('000.000.001-91'))
        for value in ('000.000.001-90', '11111111111', '0000000019', 'abc00000000191', '１２３４５６７８９０９'):
            self.assertFalse(valid_cpf(value))

    def test_no_automatic_approval_and_evidence(self):
        doc = self.ingest()
        result = self.flow.inspect(doc, self.actor)
        self.assertEqual(result['document']['state'], 'REVIEW')
        self.assertIn('000.000.001-91', result['candidates'][0]['evidence'])
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM link').fetchone()[0], 0)

    def test_idempotence_is_scoped_to_unit(self):
        first = self.ingest()
        self.assertEqual(first, self.ingest())
        second = self.flow.ingest(self.root/'input.txt', self.other)
        self.assertNotEqual(first, second)
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM audit').fetchone()[0], 2)

    def test_multiple_occurrences_are_preserved(self):
        doc = self.ingest('Titular 000.000.001-91\nRepresentante 123.456.789-09')
        result = self.flow.inspect(doc, self.actor)
        self.assertEqual(len(result['candidates']), 2)
        self.assertEqual(result['document']['state'], 'REVIEW')

    def test_reject_invalid_candidate(self):
        doc = self.ingest('CPF 000.000.001-90')
        with self.assertRaises(RuleError):
            self.approve(doc)
        self.assertEqual(self.flow.inspect(doc, self.actor)['document']['state'], 'REVIEW')

    def test_deny_cross_unit_and_auditor_writes(self):
        doc = self.ingest()
        with self.assertRaises(PermissionError):
            self.flow.inspect(doc, self.other)
        with self.assertRaises(PermissionError):
            self.approve(doc, actor=Actor('Auditor', 'auditor', 'A'))
        with self.assertRaises(RuleError):
            self.approve(doc, credit_id='b1')

    def test_deny_wrong_subject_or_unconfirmed_role(self):
        doc = self.ingest()
        with self.assertRaises(RuleError):
            self.approve(doc, credit_id='a2')
        with self.assertRaises(RuleError):
            self.approve(doc, subject_confirmed=False)

    def test_candidate_must_belong_to_document(self):
        doc = self.ingest()
        other = self.ingest('Outro documento CPF 000.000.001-91', 'other.txt')
        candidate = self.flow.inspect(other, self.actor)['candidates'][0]['id']
        with self.assertRaises(RuleError):
            self.approve(doc, candidate_id=candidate)

    def test_stale_second_connection_cannot_overwrite(self):
        doc = self.ingest()
        second = Store(self.root/'test.sqlite')
        try:
            flow2 = Workflow(second, LocalTextExtractor())
            version = flow2.inspect(doc, self.actor)['document']['version']
            self.approve(doc)
            with self.assertRaises(RuleError):
                flow2.decide(doc, self.actor, version, False, 'Decisão antiga')
            self.assertEqual(flow2.inspect(doc, self.actor)['document']['state'], 'APPROVED')
        finally:
            second.close()

    def test_audit_failure_rolls_back_link_and_state(self):
        doc = self.ingest()
        self.store.db.execute("CREATE TRIGGER fail_event BEFORE INSERT ON audit WHEN NEW.event='APPROVED' BEGIN SELECT RAISE(ABORT,'Falha de ensaio'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.approve(doc)
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM link').fetchone()[0], 0)
        self.assertEqual(self.flow.inspect(doc, self.actor)['document']['state'], 'REVIEW')

    def test_missing_text_requires_ocr_and_cannot_approve(self):
        path = self.root/'scan.pdf'
        pdf = PdfWriter(); pdf.add_blank_page(width=300, height=300)
        with path.open('wb') as f:
            pdf.write(f)
        doc = self.flow.ingest(path, self.actor)
        self.assertEqual(self.flow.inspect(doc, self.actor)['document']['state'], 'OCR_REQUIRED')
        with self.assertRaises(RuleError):
            self.flow.decide(doc, self.actor, 1, True, 'Ensaio', 1, 'a1', True)

    def test_text_pdf_extracts_evidence_and_preserves_leading_zero(self):
        path = Path(__file__).resolve().parents[1]/'examples'/'requerimento_sintetico.pdf'
        doc = self.flow.ingest(path, self.actor)
        result = self.flow.inspect(doc, self.actor)
        self.assertEqual(result['document']['state'], 'REVIEW')
        self.assertEqual(result['candidates'][0]['cpf'], '00000000191')
        self.assertEqual(result['candidates'][0]['page'], 1)
        self.assertIn('contribuinte ficticio', result['candidates'][0]['evidence'])

    def test_no_cpf_rejection_and_append_only_events(self):
        doc = self.ingest('Documento sem identificador')
        self.assertEqual(self.flow.inspect(doc, self.actor)['document']['state'], 'NO_CPF')
        self.flow.decide(doc, self.actor, 1, False, 'Solicitada complementação')
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.db.execute('DELETE FROM audit')
        self.assertEqual(self.flow.inspect(doc, self.actor)['document']['state'], 'REJECTED')


if __name__ == '__main__':
    unittest.main()
