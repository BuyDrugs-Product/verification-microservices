# AI PROMPT: ENHANCE PHARMTECH TEST SUITE WITH REAL TEST DATA

## PROBLEM STATEMENT

The current PharmTech test suite needs improvement to match the facilities service quality. We have real license numbers and their expected responses to build comprehensive tests.

## REAL TEST DATA PROVIDED

### Test Case 1: PT2025D09630
**Expected Data**:
- **Name**: "Kimutai Abel"
- **License**: "PT2025D09630" 
- **Status**: "Active"
- **Valid Till**: "2025-12-31"
- **Photo URL**: "http://rhris.pharmacyboardkenya.org/photos/9b0a620f6d8860a.JPG"

### Test Case 2: PT2025D07035
**Expected Data**:
- **Name**: "Gitau Alex Njuguna"
- **License**: "PT2025D07035"
- **Status**: "Active" 
- **Valid Till**: "2025-12-31"
- **Photo URL**: "http://rhris.pharmacyboardkenya.org/photos/9b0f3c77e804a579337d0b446.JPG"

## TEST SUITE REQUIREMENTS

### 1. COMPREHENSIVE TEST DATA
```python
REAL_PHARMTECH_TEST_CASES = [
    {
        "license_number": "PT2025D09630",
        "expected_data": {
            "full_name": "Kimutai Abel",
            "practice_license_number": "PT2025D09630",
            "status": "Active",
            "valid_till": "2025-12-31",
            "photo_url": "http://rhris.pharmacyboardkenya.org/photos/9b0a620f6d8860a.JPG"
        }
    },
    {
        "license_number": "PT2025D07035", 
        "expected_data": {
            "full_name": "Gitau Alex Njuguna",
            "practice_license_number": "PT2025D07035",
            "status": "Active",
            "valid_till": "2025-12-31",
            "photo_url": "http://rhris.pharmacyboardkenya.org/photos/9b0f3c77e804a579337d0b446.JPG"
        }
    }
]

ERROR_TEST_CASES = [
    {
        "license_number": "PT99999999",
        "expected_error": "PharmTech license not found"
    },
    {
        "license_number": "INVALID123",
        "expected_error": "Invalid license number format"
    },
    {
        "license_number": "PT2025",  # Too short
        "expected_error": "Invalid license number format"
    }
]
```

### 2. ENHANCED TEST STRUCTURE

#### `tests/test_direct.py` - Main Test Runner
```python
#!/usr/bin/env python3
"""
PharmTech Verification Test Suite
Run with: python tests/test_direct.py
"""

import sys
import time
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pharmtech_verifier import verify_pharmtech

def run_tests():
    """Main test runner matching facilities service quality"""
    print("🧪 PHARMTECH VERIFICATION TEST SUITE")
    print("=" * 50)
    
    test_results = {
        'passed': 0,
        'failed': 0,
        'total_time': 0
    }
    
    # Test 1: Valid License Verification
    print("\n1. Testing Valid License Verification...")
    for test_case in REAL_PHARMTECH_TEST_CASES:
        start_time = time.time()
        result = verify_pharmtech(test_case["license_number"])
        end_time = time.time()
        
        processing_time = (end_time - start_time) * 1000
        test_results['total_time'] += processing_time
        
        if validate_verification_result(result, test_case):
            print(f"   ✅ {test_case['license_number']}: PASSED ({processing_time:.2f}ms)")
            test_results['passed'] += 1
        else:
            print(f"   ❌ {test_case['license_number']}: FAILED")
            test_results['failed'] += 1
    
    # Test 2: Error Handling
    print("\n2. Testing Error Handling...")
    for test_case in ERROR_TEST_CASES:
        result = verify_pharmtech(test_case["license_number"])
        
        if validate_error_result(result, test_case):
            print(f"   ✅ {test_case['license_number']}: Correctly handled")
            test_results['passed'] += 1
        else:
            print(f"   ❌ {test_case['license_number']}: Error not properly handled")
            test_results['failed'] += 1
    
    # Test 3: Performance
    print("\n3. Testing Performance...")
    performance_ok = test_performance()
    if performance_ok:
        print("   ✅ Performance: All requests under 3 seconds")
        test_results['passed'] += 1
    else:
        print("   ❌ Performance: Some requests too slow")
        test_results['failed'] += 1
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print(f"   Passed: {test_results['passed']}")
    print(f"   Failed: {test_results['failed']}")
    print(f"   Total: {test_results['passed'] + test_results['failed']}")
    print(f"   ⏱️  Average time: {test_results['total_time']/len(REAL_PHARMTECH_TEST_CASES):.2f}ms")
    
    if test_results['failed'] == 0:
        print("🎉 ALL TESTS PASSED!")
        return 0
    else:
        print("❌ SOME TESTS FAILED!")
        return 1

def validate_verification_result(result, test_case):
    """Validate successful verification results"""
    expected = test_case["expected_data"]
    
    checks = [
        result.get("success") == True,
        result.get("license_number") == test_case["license_number"],
        result.get("data", {}).get("full_name") == expected["full_name"],
        result.get("data", {}).get("practice_license_number") == expected["practice_license_number"],
        result.get("data", {}).get("status") == expected["status"],
        result.get("data", {}).get("valid_till") == expected["valid_till"],
        result.get("data", {}).get("photo_url") == expected["photo_url"],
        result.get("processing_time_ms", 0) < 3000  # Under 3 seconds
    ]
    
    return all(checks)

def validate_error_result(result, test_case):
    """Validate error handling results"""
    return (
        result.get("success") == False and
        test_case["expected_error"] in result.get("message", "")
    )

def test_performance():
    """Test that all requests complete within acceptable time"""
    for test_case in REAL_PHARMTECH_TEST_CASES[:2]:  # Test first 2
        start_time = time.time()
        result = verify_pharmtech(test_case["license_number"])
        end_time = time.time()
        
        if (end_time - start_time) > 3.0:  # 3 seconds max
            return False
            
        if not result.get("success"):
            return False
            
    return True

if __name__ == "__main__":
    sys.exit(run_tests())
```

### 3. SPECIFIC TEST MODULES

#### `tests/test_verification.py`
```python
import pytest
from pharmtech_verifier import verify_pharmtech

class TestPharmTechVerification:
    """Test PharmTech license verification with real data"""
    
    def test_kimutai_abel_verification(self):
        """Test PT2025D09630 - Kimutai Abel"""
        result = verify_pharmtech("PT2025D09630")
        
        assert result["success"] == True
        assert result["license_number"] == "PT2025D09630"
        assert result["data"]["full_name"] == "Kimutai Abel"
        assert result["data"]["practice_license_number"] == "PT2025D09630"
        assert result["data"]["status"] == "Active"
        assert result["data"]["valid_till"] == "2025-12-31"
        assert "9b0a620f6d8860a.JPG" in result["data"]["photo_url"]
    
    def test_gitau_alex_verification(self):
        """Test PT2025D07035 - Gitau Alex Njuguna"""
        result = verify_pharmtech("PT2025D07035")
        
        assert result["success"] == True
        assert result["license_number"] == "PT2025D07035"
        assert result["data"]["full_name"] == "Gitau Alex Njuguna"
        assert result["data"]["practice_license_number"] == "PT2025D07035"
        assert result["data"]["status"] == "Active"
        assert result["data"]["valid_till"] == "2025-12-31"
        assert "9b0f3c77e804a579337d0b446.JPG" in result["data"]["photo_url"]
```

#### `tests/test_errors.py`
```python
import pytest
from pharmtech_verifier import verify_pharmtech

class TestErrorHandling:
    """Test error scenarios"""
    
    def test_license_not_found(self):
        """Test non-existent license"""
        result = verify_pharmtech("PT99999999")
        
        assert result["success"] == False
        assert "not found" in result["message"].lower()
    
    def test_invalid_license_format(self):
        """Test malformed license numbers"""
        result = verify_pharmtech("INVALID123")
        
        assert result["success"] == False
        assert "invalid" in result["message"].lower()
```

### 4. UPDATED README.MD

```markdown
## Testing

### Quick Test
Run the complete test suite with one command:

```bash
python tests/test_direct.py
```

### Test Data
The tests use real PharmTech licenses from the PPB portal:

- **PT2025D09630**: Kimutai Abel (with photo)
- **PT2025D07035**: Gitau Alex Njuguna (with photo)

### Test Categories
- **Verification Tests**: Real license validation and data extraction
- **Error Tests**: Invalid inputs and error handling  
- **Performance Tests**: Response times under 3 seconds

### Running Specific Tests
```bash
# Run all tests
python tests/test_direct.py

# Run only verification tests
python -m pytest tests/test_verification.py -v

# Run error handling tests
python -m pytest tests/test_errors.py -v

# Run with detailed output
python tests/test_direct.py --verbose
```

### Expected Output
```
🧪 PHARMTECH VERIFICATION TEST SUITE
=====================================

1. Testing Valid License Verification...
   ✅ PT2025D09630: PASSED (1850.25ms)
   ✅ PT2025D07035: PASSED (1920.50ms)

2. Testing Error Handling...
   ✅ PT99999999: Correctly handled
   ✅ INVALID123: Error not properly handled

3. Testing Performance...
   ✅ Performance: All requests under 3 seconds

📊 TEST SUMMARY
   Passed: 4
   Failed: 0
   Total: 4
   ⏱️  Average time: 1885.38ms

🎉 ALL TESTS PASSED!
```
```

## SUCCESS CRITERIA

- ✅ **Single command**: `python tests/test_direct.py` runs all tests
- ✅ **Real data validation**: Tests use actual PPB license numbers
- ✅ **Comprehensive coverage**: Verification, errors, performance
- ✅ **Clear output**: Professional reporting matching facilities service
- ✅ **Performance benchmarks**: All tests complete under 3 seconds
- ✅ **Error handling**: Proper validation of all error scenarios
- ✅ **Easy maintenance**: Clear test structure for adding new cases

The test suite should provide the same level of confidence and professionalism as the facilities service tests, using real-world data to validate the PharmTech verification functionality.