import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.core.nlp_engine import NLPEngine

def test_user_scenarios():
    nlp = NLPEngine()
    
    # User's reported values and ranges
    test_cases = [
        {"name": "Hemoglobin", "value": "13.7", "min": 13.0, "max": 17.0, "expected": "NORMAL"},
        {"name": "WBC", "value": "8120", "min": 4000, "max": 11000, "expected": "NORMAL"},
        {"name": "Lymphocytes", "value": "13.3", "min": 20.0, "max": 40.0, "expected": "LOW"},
        {"name": "Eosinophils", "value": "0.3", "min": 1.0, "max": 6.0, "expected": "LOW"},
        {"name": "Neutrophils", "value": "76.8", "min": 40.0, "max": 80.0, "expected": "NORMAL"},
    ]
    
    print("Running Medical Reliability Verification...")
    print("-" * 50)
    
    all_passed = True
    for case in test_cases:
        test_data = {
            "test_name": case["name"],
            "value": case["value"],
            "normal_range": {"min": case["min"], "max": case["max"]}
        }
        status = nlp._classify_abnormality(test_data)
        
        passed = status == case["expected"]
        if not passed:
            all_passed = False
            
        print(f"Test: {case['name']:12} | Value: {case['value']:5} | Range: {case['min']}-{case['max']} | Status: {status:10} | {'PASSED' if passed else 'FAILED'}")

    print("-" * 50)
    if all_passed:
        print("RESULT: ALL FIXES VERIFIED SUCCESSFULLY")
    else:
        print("RESULT: SOME VERIFICATIONS FAILED")

if __name__ == "__main__":
    test_user_scenarios()
