import pandas as pd
import sys
from unittest.mock import MagicMock
from datetime import date

# Mock dependencies to test logic without DB
sys.modules['database.connection'] = MagicMock()
sys.modules['utils.date_utils'] = MagicMock()
sys.modules['utils.text_utils'] = MagicMock()
sys.modules['config'] = MagicMock()

# Setup mocks
sys.modules['database.connection'].get_connection.return_value = MagicMock()
sys.modules['utils.text_utils'].normalize_passport = lambda x: x.upper().strip()
sys.modules['utils.text_utils'].normalize_header = lambda x: x.lower().strip()
sys.modules['config'].HEADER_MAP = {'passport': 'so_ho_chieu', 'name': 'ho_ten', 'arrival': 'ngay_den'}

# Mock date utils
mock_date_utils = MagicMock()
mock_date_utils.format_date_for_db.side_effect = lambda x: x
sys.modules['utils.date_utils'] = mock_date_utils

# Import target
from modules.import_data import _process_dataframe

# Helper to mock date formatting
def mock_format_date(val):
    return val

sys.modules['modules.import_data'].safe_format_date = mock_format_date

# Create test dataframe
data = [
    {'so_ho_chieu': 'ABC12345', 'ho_ten': 'Valid Person', 'ngay_den': '2025-01-01', 'ngay_di': '2025-02-01'},
    {'so_ho_chieu': '', 'ho_ten': 'Empty Passport', 'ngay_den': '2025-01-01'},  # Invalid: Empty passport
    {'so_ho_chieu': 'XYZ', 'ho_ten': 'Short Passport', 'ngay_den': '2025-01-01'}, # Invalid: Short passport
    {'so_ho_chieu': 'FUTURE123', 'ho_ten': 'Future Date', 'ngay_den': '2099-01-01'}, # Invalid: Future date
    {'so_ho_chieu': 'VALID999', 'ho_ten': 'Another Valid', 'ngay_den': '2025-01-01'}
]
df = pd.DataFrame(data)

# Run process
print("Running _process_dataframe with test data...")
try:
    result = _process_dataframe(df, "test.xlsx")
    print("\nResult:")
    print(f"Success: {result['success']}")
    print(f"Rows Imported: {result['rows_imported']}")
    print(f"Rows Skipped: {result['rows_skipped']}")
    if 'validation_report' in result:
        print(f"Total Errors: {result['validation_report']['total_errors']}")
        print("First Error Details:")
        for err in result['validation_report']['details'][:3]:
             print(f" - Row {err['errors'][0]['row']}: {err['errors'][0]['message']}")
             
except Exception as e:
    print(f"Crash: {e}")
    import traceback
    traceback.print_exc()
