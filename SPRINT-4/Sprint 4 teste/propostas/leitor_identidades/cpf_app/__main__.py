import argparse
import json
from pathlib import Path
from .domain import Actor
from .extraction import LocalTextExtractor
from .storage import Store
from .service import Workflow


def main():
    parser = argparse.ArgumentParser(description='MVP local: somente dados sintéticos; ator simulado, sem autenticação.')
    parser.add_argument('--db', default='demo.sqlite')
    parser.add_argument('--actor', choices=['servidor_a', 'servidor_b', 'auditor_a'], default='servidor_a')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('seed-demo')
    ingest = sub.add_parser('ingest'); ingest.add_argument('file')
    inspect = sub.add_parser('inspect'); inspect.add_argument('document', type=int)
    decide = sub.add_parser('decide')
    decide.add_argument('document', type=int)
    decide.add_argument('--version', type=int, required=True)
    decide.add_argument('--approve', action='store_true')
    decide.add_argument('--candidate', type=int)
    decide.add_argument('--credit')
    decide.add_argument('--subject-confirmed', action='store_true')
    decide.add_argument('--reason', required=True)
    args = parser.parse_args()
    actors = {'servidor_a': Actor('servidor_a', 'reviewer', 'A'),
              'servidor_b': Actor('servidor_b', 'reviewer', 'B'),
              'auditor_a': Actor('auditor_a', 'auditor', 'A')}
    actor = actors[args.actor]
    store = Store(args.db)
    flow = Workflow(store, LocalTextExtractor())
    try:
        if args.command == 'seed-demo':
            with store.db:
                store.db.executemany('INSERT OR IGNORE INTO credit VALUES (?,?,?,?)', [
                    ('IPTU-DEMO-A', 'A', '00000000191', 'Crédito inteiramente fictício A'),
                    ('IPTU-DEMO-B', 'B', '00000000191', 'Crédito inteiramente fictício B')])
            result = {'status': 'fixtures sintéticas inseridas; não consultadas em bases reais'}
        elif args.command == 'ingest':
            result = {'document_id': flow.ingest(args.file, actor)}
        elif args.command == 'inspect':
            result = flow.inspect(args.document, actor)
        else:
            flow.decide(args.document, actor, args.version, args.approve, args.reason,
                        args.candidate, args.credit, args.subject_confirmed)
            result = {'status': 'decisão registrada'}
        print(json.dumps(result, ensure_ascii=True, indent=2))
    except (ValueError, PermissionError, OSError) as error:
        parser.exit(1, str(error)+'\n')
    finally:
        store.close()


if __name__ == '__main__':
    main()
