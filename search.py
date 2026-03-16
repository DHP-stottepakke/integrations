# search.py
import json
import os
from flask import Flask, request, jsonify
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Configuration from environment variables
CONFIG = {
    'data_file': os.getenv('DATA_FILE', 'policies.json'),
    'case_sensitive': False,
    'search_fields': ['name', 'alternateName'],
    'match_type': 'partial',
}
# Global variable to store the data
data = None

def load_data():
    """Load JSON-LD data from file."""
    global data
    try:
        with open(CONFIG['data_file'], 'r', encoding='utf-8') as f:
            data = json.load(f)
        return True
    except FileNotFoundError:
        print(f"Error: {CONFIG['data_file']} not found")
        return False
    except json.JSONDecodeError:
        print(f"Error: {CONFIG['data_file']} is not valid JSON")
        return False

def extract_name_value(name_field: Any) -> str:
    """
    Extract the name value from a name field.
    Handles both string and object formats (with @language and @value).
    """
    if isinstance(name_field, str):
        return name_field
    elif isinstance(name_field, dict):
        return name_field.get('@value', '')
    elif isinstance(name_field, list):
        # Return the first English name, or first name if no English
        for item in name_field:
            if isinstance(item, dict):
                if item.get('@language') == 'en':
                    return item.get('@value', '')
        # Fallback to first item
        if name_field:
            return extract_name_value(name_field[0])
    return ''

def matches_search(item: Dict[str, Any], search_term: str) -> bool:
    """Check if an organization item matches the search term."""
    search_term_processed = search_term if CONFIG['case_sensitive'] else search_term.lower()
    
    for field in CONFIG['search_fields']:
        if field not in item:
            continue
        
        field_value = item[field]
        
        # Handle 'name' field which can be string, list, or object
        if field == 'name':
            if isinstance(field_value, list):
                for name_item in field_value:
                    name_str = extract_name_value(name_item)
                    name_processed = name_str if CONFIG['case_sensitive'] else name_str.lower()
                    if matches_string(name_processed, search_term_processed):
                        return True
            else:
                name_str = extract_name_value(field_value)
                name_processed = name_str if CONFIG['case_sensitive'] else name_str.lower()
                if matches_string(name_processed, search_term_processed):
                    return True
        else:
            # Handle simple string fields
            if isinstance(field_value, str):
                field_processed = field_value if CONFIG['case_sensitive'] else field_value.lower()
                if matches_string(field_processed, search_term_processed):
                    return True
    
    return False

def matches_string(field_value: str, search_term: str) -> bool:
    """Check if a string field matches the search term based on match_type."""
    if CONFIG['match_type'] == 'exact':
        return field_value == search_term
    else:  # partial
        return search_term in field_value

def filter_items(search_term: str) -> List[Dict[str, Any]]:
    """Filter itemListElement based on search term."""
    if not data or 'itemListElement' not in data:
        return []
    
    if not search_term or search_term.strip() == '':
        return data['itemListElement']
    
    filtered = []
    for item in data['itemListElement']:
        if 'item' in item and matches_search(item['item'], search_term):
            filtered.append(item)
    
    return filtered

@app.route('/search', methods=['GET'])
def search():
    """
    Search for institutional policies by organization name.
    
    Query Parameters:
    - q: Search term (required)
    - case_sensitive: true/false - Case sensitivity (optional, default: false)
    - match_type: 'partial' or 'exact' - Type of matching (optional, default: partial)
    - search_fields: Comma-separated list of fields to search (optional, default: name,alternateName)
    
    Example: /search?q=University&case_sensitive=false&match_type=partial
    """
    
    # Get search parameters
    search_term = request.args.get('q', '').strip()
    
    # Get optional configuration overrides
    case_sensitive = request.args.get('case_sensitive', 'false').lower() == 'true'
    match_type = request.args.get('match_type', 'partial')
    search_fields = request.args.get('search_fields', 'name,alternateName').split(',')
    
    # Validate match_type
    if match_type not in ['partial', 'exact']:
        return jsonify({'error': "match_type must be 'partial' or 'exact'"}), 400
    
    # Validate search_fields
    valid_fields = ['name', 'alternateName', 'url', 'identifier']
    search_fields = [f.strip() for f in search_fields if f.strip() in valid_fields]
    
    if not search_fields:
        search_fields = ['name', 'alternateName']
    
    # Apply configuration overrides
    CONFIG['case_sensitive'] = case_sensitive
    CONFIG['match_type'] = match_type
    CONFIG['search_fields'] = search_fields
    
    # Perform search
    filtered_items = filter_items(search_term)
    
    # Build response with same structure as input
    response = {
        '@context': data.get('@context'),
        '@type': data.get('@type'),
        'name': data.get('name'),
        'itemListElement': filtered_items,
        'search_params': {
            'query': search_term,
            'case_sensitive': case_sensitive,
            'match_type': match_type,
            'search_fields': CONFIG['search_fields'],
            'results_count': len(filtered_items)
        }
    }
    
    return jsonify(response)

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok', 'data_loaded': data is not None})

@app.route('/config', methods=['GET'])
def get_config():
    """Get current configuration."""
    return jsonify({
        'case_sensitive': CONFIG['case_sensitive'],
        'match_type': CONFIG['match_type'],
        'search_fields': CONFIG['search_fields'],
        'data_file': CONFIG['data_file']
    })

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Endpoint not found. Try /search?q=your_query'}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    if load_data():
        print(f"✓ Data loaded from {CONFIG['data_file']}")
        print("✓ Flask app started on http://127.0.0.1:5000")
        print("✓ Try: http://127.0.0.1:5000/search?q=University")
        app.run(debug=True, host='127.0.0.1', port=5000)
    else:
        print("✗ Failed to load data. Exiting.")
        exit(1)
