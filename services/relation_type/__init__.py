# relation_type blueprint — search API over the combined DataCite relationType vocab.
#
# The combined JSON-LD document (relationType.jsonld) is produced by build.py from the
# DataCite schema.datacite.org-linked-data repo (Apache-2.0). See LICENSE and NOTICE here.
import os
import json
from typing import Any, Dict, List, Optional
from flask import Blueprint, request, jsonify

bp = Blueprint('relation_type', __name__)

_HERE = os.path.dirname(__file__)
_DATA_FILE = os.getenv('RELATIONTYPE_DATA_FILE', os.path.join(_HERE, 'relationType.jsonld'))

_doc: Optional[Dict[str, Any]] = None
_concepts: List[Dict[str, Any]] = []        # @graph nodes of type Concept
_search_texts: List[str] = []               # parallel to _concepts, lowercased prefLabel+definition


def _text(value: Any) -> str:
    """Flatten a JSON-LD value (str / {@value} / list) into plain text."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return value.get('@value', '')
    if isinstance(value, list):
        return " ".join(_text(v) for v in value)
    return ''


def load_data() -> bool:
    global _doc, _concepts, _search_texts
    try:
        with open(_DATA_FILE, 'r', encoding='utf-8') as f:
            _doc = json.load(f)
    except FileNotFoundError:
        print(f"Error: {_DATA_FILE} not found")
        return False
    except Exception as e:
        print(f"Error loading {_DATA_FILE}: {e}")
        return False

    _concepts = [n for n in _doc.get('@graph', []) if n.get('type') == 'Concept']
    _search_texts = [
        (f"{_text(c.get('prefLabel'))} {_text(c.get('definition'))}").lower()
        for c in _concepts
    ]
    return True


def loaded() -> bool:
    return _doc is not None


@bp.route('/datacite/relationtype', methods=['GET'])
def full_doc():
    """Return the full combined JSON-LD vocabulary document."""
    if _doc is None:
        return jsonify({'error': 'data not loaded'}), 503
    return jsonify(_doc)


@bp.route('/datacite/relationtype/search', methods=['GET'])
def search():
    """Simple case-insensitive partial search over prefLabel and definition."""
    q = request.args.get('q', '').strip().lower()
    if q:
        results = [c for c, txt in zip(_concepts, _search_texts) if q in txt]
    else:
        results = list(_concepts)

    return jsonify({
        '@context': _doc.get('@context') if _doc else None,
        'query': request.args.get('q', '').strip(),
        'count': len(results),
        'results': results,
    })


# Load once at import time so Gunicorn --preload benefits. Don't abort on
# failure: the app still starts and /health reports the degraded state
# (loaded() == False). /datacite/relationtype returns 503 until data loads.
if not load_data():
    print("relation_type: WARNING failed to load data; /health will report degraded")
