# search.py
import os
from typing import List, Dict, Any, Optional
from flask import Flask, request, jsonify

# dev-only dotenv
if os.environ.get("ENV", os.environ.get("FLASK_ENV", "development")) != "production":
    try:
        from dotenv import load_dotenv, find_dotenv
        dotenv_path = find_dotenv(usecwd=True)
        if dotenv_path:
            load_dotenv(dotenv_path)
    except Exception:
        pass

app = Flask(__name__)

# Configuration defaults
CONFIG = {
    'data_file': os.getenv('DATA_FILE', 'policies.json'),
    'case_sensitive': False,
    'search_fields': ['name', 'alternateName'],
    'match_type': 'partial',
}

# In-memory structures populated at startup
_data_raw: Optional[Dict[str, Any]] = None
_item_list: List[Dict[str, Any]] = []
_search_texts: List[str] = []  # parallel to _item_list, precomputed searchable text per item

# prefer orjson for speed
try:
    import orjson as _json
    def loads(fp):
        return _json.loads(fp.read())
except Exception:
    import json as _json
    def loads(fp):
        return _json.load(fp)

def extract_name_value(name_field: Any) -> str:
    if isinstance(name_field, str):
        return name_field
    if isinstance(name_field, dict):
        return name_field.get('@value', '')
    if isinstance(name_field, list):
        for item in name_field:
            if isinstance(item, dict) and item.get('@language') == 'en':
                return item.get('@value', '')
        if name_field:
            return extract_name_value(name_field[0])
    return ''

def _build_searchable_text(item: Dict[str, Any], fields: List[str]) -> str:
    parts: List[str] = []
    for field in fields:
        if field not in item:
            continue
        val = item[field]
        if field == 'name':
            if isinstance(val, list):
                for ni in val:
                    parts.append(extract_name_value(ni))
            else:
                parts.append(extract_name_value(val))
        elif isinstance(val, str):
            parts.append(val)
    return " ".join(p for p in parts if p)

def load_data() -> bool:
    global _data_raw, _item_list, _search_texts
    try:
        with open(CONFIG['data_file'], 'rb') as f:
            _data_raw = loads(f)
    except FileNotFoundError:
        print(f"Error: {CONFIG['data_file']} not found")
        return False
    except Exception as e:
        print(f"Error loading JSON: {e}")
        return False

    items = _data_raw.get('itemListElement', [])
    _item_list = items

    # Precompute searchable text for each item (lowercased)
    default_fields = ['name', 'alternateName']
    _search_texts = []
    for el in items:
        itm = el.get('item', {})
        txt = _build_searchable_text(itm, default_fields + ['identifier', 'url'])
        _search_texts.append(txt.lower())
    return True

def _match_precomputed(idx: int, search_term: str, match_type: str, case_sensitive: bool) -> bool:
    field_text = _search_texts[idx] if not case_sensitive else _build_searchable_text(_item_list[idx].get('item', {}), CONFIG['search_fields'])
    if not case_sensitive:
        if match_type == 'exact':
            return field_text == search_term
        return search_term in field_text
    else:
        if match_type == 'exact':
            return field_text == search_term
        return search_term in field_text

def filter_items(search_term: str, search_fields: List[str], match_type: str, case_sensitive: bool) -> List[Dict[str, Any]]:
    if not _item_list:
        return []
    if not search_term:
        return _item_list

    term = search_term if case_sensitive else search_term.lower()
    results = []
    # Loop over precomputed texts (fast string ops)
    for idx, el in enumerate(_item_list):
        if _match_precomputed(idx, term, match_type, case_sensitive):
            results.append(el)
    return results

@app.route('/search', methods=['GET'])
def search():
    q = request.args.get('q', '').strip()
    case_sensitive = request.args.get('case_sensitive', 'false').lower() == 'true'
    match_type = request.args.get('match_type', 'partial')
    search_fields = [f.strip() for f in request.args.get('search_fields', 'name,alternateName').split(',') if f.strip()]

    if match_type not in ('partial', 'exact'):
        return jsonify({'error': "match_type must be 'partial' or 'exact'"}), 400

    valid_fields = {'name', 'alternateName', 'url', 'identifier'}
    search_fields = [f for f in search_fields if f in valid_fields] or ['name', 'alternateName']

    results = filter_items(q, search_fields, match_type, case_sensitive)

    response = {
        '@context': _data_raw.get('@context') if _data_raw else None,
        '@type': _data_raw.get('@type') if _data_raw else None,
        'name': _data_raw.get('name') if _data_raw else None,
        'itemListElement': results,
        'search_params': {
            'query': q,
            'case_sensitive': case_sensitive,
            'match_type': match_type,
            'search_fields': search_fields,
            'results_count': len(results)
        }
    }
    return jsonify(response)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'data_loaded': bool(_data_raw)})

@app.route('/config', methods=['GET'])
def get_config():
    return jsonify({
        'case_sensitive': CONFIG['case_sensitive'],
        'match_type': CONFIG['match_type'],
        'search_fields': CONFIG['search_fields'],
        'data_file': CONFIG['data_file']
    })

# Load data at import time so Gunicorn --preload benefits
if not load_data():
    print("✗ Failed to load data. Exiting.")
    raise SystemExit(1)

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
