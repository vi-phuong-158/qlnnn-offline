"""
QLNNN Offline - Data Validators
Validation framework for import data
"""

from dataclasses import dataclass, field
from typing import List, Optional, Any
from datetime import date, datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import CONTINENT_RULES


@dataclass
class ValidationError:
    """Represents a single validation error or warning."""
    row: int
    column: str
    message: str
    value: Any = None
    severity: str = 'error'  # 'error' | 'warning'


@dataclass
class ValidationResult:
    """Container for validation results."""
    is_valid: bool = True
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    
    @property
    def error_count(self) -> int:
        return len(self.errors)
    
    @property
    def warning_count(self) -> int:
        return len(self.warnings)
    
    def add_error(self, row: int, column: str, message: str, value: Any = None):
        self.errors.append(ValidationError(
            row=row, column=column, message=message, 
            value=value, severity='error'
        ))
        self.is_valid = False
    
    def add_warning(self, row: int, column: str, message: str, value: Any = None):
        self.warnings.append(ValidationError(
            row=row, column=column, message=message,
            value=value, severity='warning'
        ))
    
    def to_dict(self) -> dict:
        return {
            'is_valid': self.is_valid,
            'error_count': self.error_count,
            'warning_count': self.warning_count,
            'errors': [
                {'row': e.row, 'column': e.column, 'message': e.message, 'value': str(e.value)}
                for e in self.errors[:50]  # Limit to first 50
            ],
            'warnings': [
                {'row': w.row, 'column': w.column, 'message': w.message, 'value': str(w.value)}
                for w in self.warnings[:50]
            ]
        }


class ImportValidator:
    """Validator for Excel/CSV import data."""
    
    def __init__(self):
        self.result = ValidationResult()
        self._all_countries = self._build_country_set()
    
    def _build_country_set(self) -> set:
        """Build set of all known country codes/names."""
        countries = set()
        for country_list in CONTINENT_RULES.values():
            countries.update(c.upper() for c in country_list)
        return countries
    
    def validate_passport(self, passport: str, row: int) -> bool:
        """
        Validate passport format.
        
        Requirements:
        - Not empty
        - At least 5 characters
        - Alphanumeric after normalization
        """
        if not passport or str(passport).strip() == '':
            self.result.add_error(
                row=row, column='so_ho_chieu',
                message='Số hộ chiếu không được để trống',
                value=passport
            )
            return False
        
        # Normalize
        normalized = str(passport).upper().strip().replace(' ', '').replace('-', '')
        
        if len(normalized) < 5:
            self.result.add_error(
                row=row, column='so_ho_chieu',
                message=f'Số hộ chiếu quá ngắn (tối thiểu 5 ký tự)',
                value=passport
            )
            return False
        
        if not normalized.isalnum():
            self.result.add_error(
                row=row, column='so_ho_chieu',
                message='Số hộ chiếu chỉ được chứa chữ và số',
                value=passport
            )
            return False
        
        return True
    
    def validate_date_not_future(
        self, 
        value: Any, 
        row: int, 
        column: str,
        allow_today: bool = True
    ) -> bool:
        """Validate that a date is not in the future."""
        if value is None or str(value).strip() == '' or str(value).lower() == 'nan':
            return True  # Empty dates are valid (optional field)
        
        today = date.today()
        
        # Handle various date types
        try:
            if isinstance(value, str):
                # Try parsing YYYY-MM-DD
                check_date = datetime.strptime(value, '%Y-%m-%d').date()
            elif isinstance(value, datetime):

                check_date = value.date()
            elif isinstance(value, date):
                check_date = value
            else:
                return True
        except ValueError:
            return True  # Invalid format handled elsewhere or ignored
        
        if allow_today:
            if check_date > today:
                self.result.add_error(
                    row=row, column=column,
                    message=f'Ngày không thể nằm trong tương lai',
                    value=str(check_date)
                )
                return False
        else:
            if check_date >= today:
                self.result.add_error(
                    row=row, column=column,
                    message=f'Ngày phải trước ngày hiện tại',
                    value=str(check_date)
                )
                return False
        
        return True
    
    def validate_date_range(
        self, 
        ngay_den: Any, 
        ngay_di: Any, 
        row: int
    ) -> bool:
        """Validate that departure date is not before arrival date."""
        if ngay_den is None or ngay_di is None:
            return True
        
        # Convert to date objects
        try:
            if isinstance(ngay_den, str):
                arrival = datetime.strptime(ngay_den, '%Y-%m-%d').date()
            elif isinstance(ngay_den, datetime):
                arrival = ngay_den.date()
            elif isinstance(ngay_den, date):
                arrival = ngay_den
            else:
                return True
                
            if isinstance(ngay_di, str):
                departure = datetime.strptime(ngay_di, '%Y-%m-%d').date()
            elif isinstance(ngay_di, datetime):
                departure = ngay_di.date()
            elif isinstance(ngay_di, date):
                departure = ngay_di
            else:
                return True
        except ValueError:
            return True
        
        if departure < arrival:
            self.result.add_error(
                row=row, column='ngay_di',
                message=f'Ngày đi ({departure}) không thể trước ngày đến ({arrival})',
                value=f'{arrival} -> {departure}'
            )
            return False
        
        return True
    
    def validate_nationality(self, nationality: str, row: int) -> bool:
        """
        Validate nationality against known list.
        Only adds warning if unknown (still allows import).
        """
        if not nationality or str(nationality).strip() == '':
            return True
        
        nat_upper = str(nationality).upper().strip()
        
        if nat_upper not in self._all_countries:
            self.result.add_warning(
                row=row, column='quoc_tich',
                message=f'Quốc tịch chưa được định nghĩa trong hệ thống',
                value=nationality
            )
            return False
        
        return True
    
    def get_result(self) -> ValidationResult:
        """Get the validation result."""
        return self.result
    
    def reset(self):
        """Reset validator for new validation run."""
        self.result = ValidationResult()


def validate_import_row(row: dict, row_index: int, validator: ImportValidator = None) -> ImportValidator:
    """
    Convenience function to validate a single import row.
    
    Args:
        row: Dictionary of column -> value
        row_index: Row number (for error reporting)
        validator: Optional existing validator (creates new if None)
        
    Returns:
        ImportValidator with results
    """
    if validator is None:
        validator = ImportValidator()
    
    # Passport (required)
    validator.validate_passport(row.get('so_ho_chieu'), row_index)
    
    # Dates
    validator.validate_date_not_future(row.get('ngay_sinh'), row_index, 'ngay_sinh')
    validator.validate_date_not_future(row.get('ngay_den'), row_index, 'ngay_den')
    validator.validate_date_not_future(row.get('ngay_di'), row_index, 'ngay_di')
    
    # Date range
    validator.validate_date_range(row.get('ngay_den'), row.get('ngay_di'), row_index)
    
    # Nationality (warning only)
    validator.validate_nationality(row.get('quoc_tich'), row_index)
    
    return validator
