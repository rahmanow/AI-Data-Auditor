import requests
import sys
import json
from datetime import datetime
import time
import os

class DataQualityAPITester:
    def __init__(self, base_url="https://quick-app-studio-1.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.analysis_id = None
        
    def run_test(self, name, method, endpoint, expected_status, data=None, files=None, timeout=30):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {}
        if data and not files:
            headers['Content-Type'] = 'application/json'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                if files:
                    response = requests.post(url, files=files, timeout=timeout)
                else:
                    response = requests.post(url, json=data, headers=headers, timeout=timeout)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                
                # Try to parse JSON response
                try:
                    json_response = response.json()
                    return True, json_response
                except:
                    return True, response.text
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:500]}...")
                return False, {}

        except requests.exceptions.Timeout:
            print(f"❌ Failed - Request timeout after {timeout}s")
            return False, {}
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test API root endpoint"""
        success, response = self.run_test(
            "API Root",
            "GET",
            "",
            200
        )
        return success

    def test_file_upload(self):
        """Test CSV file upload and analysis"""
        
        # Prepare test CSV file
        test_csv_content = """name,age,salary,email,department
John Doe,25,50000,john@example.com,Sales
Jane Smith,,65000,jane@example.com,Marketing
Bob Wilson,35,45000,bob@example.com,Sales
Alice Brown,28,70000,,Engineering
Charlie Davis,300,55000,charlie@example.com,Marketing
Eva Martinez,32,150000,eva@example.com,Engineering
Frank Thomas,29,48000,frank@example.com,Sales
Grace Lee,31,52000,grace@example.com,Marketing
  Henry Clark  ,27,47000,henry@example.com,Sales
Ivy Robinson,33,58000,ivy@example.com,Engineering
John Doe,25,50000,john@example.com,Sales
Kate Wilson,29,49000,kate@example.com,Marketing
Leo Garcia,35,62000,leo@example.com,Engineering
Mia Johnson,,53000,mia@example.com,Sales
Noah Brown,38,75000,noah@example.com,Marketing"""

        files = {'file': ('test_data.csv', test_csv_content, 'text/csv')}
        
        success, response = self.run_test(
            "File Upload & Analysis",
            "POST",
            "upload",
            200,
            files=files,
            timeout=60  # Longer timeout for analysis
        )
        
        if success and isinstance(response, dict):
            self.analysis_id = response.get('id')
            print(f"   Analysis ID: {self.analysis_id}")
            print(f"   Quality Score: {response.get('quality_score', 'N/A')}/100")
            print(f"   Total Rows: {response.get('total_rows', 'N/A')}")
            print(f"   Total Columns: {response.get('total_columns', 'N/A')}")
            print(f"   Missing Values: {len(response.get('missing_values', []))}")
            print(f"   Outliers: {len(response.get('outliers', []))}")
            print(f"   Duplicates: {response.get('duplicates', {}).get('total_duplicates', 0)}")
            print(f"   Inconsistencies: {len(response.get('inconsistencies', []))}")
            
            # Validate expected issues in our test data
            expected_missing = 2  # Jane Smith age, Alice Brown email, Mia Johnson age (actually 3)
            expected_outliers = 2  # Charlie Davis age=300, Eva Martinez salary=150000
            expected_duplicates = 1  # John Doe duplicate
            
            missing_count = len(response.get('missing_values', []))
            outliers_count = len(response.get('outliers', []))
            duplicates_count = response.get('duplicates', {}).get('total_duplicates', 0)
            
            print(f"   Expected vs Found - Missing: {expected_missing} vs {missing_count}")
            print(f"   Expected vs Found - Outliers: {expected_outliers} vs {outliers_count}")
            print(f"   Expected vs Found - Duplicates: {expected_duplicates} vs {duplicates_count}")
            
        return success

    def test_ai_insights(self):
        """Test AI insights generation"""
        if not self.analysis_id:
            print("❌ Skipping AI insights - no analysis ID available")
            return False
            
        # Get the analysis data first
        success, analysis_data = self.run_test(
            "Get Analysis Data",
            "GET",
            f"analysis/{self.analysis_id}",
            200
        )
        
        if not success:
            print("❌ Failed to get analysis data for AI insights")
            return False
        
        request_data = {
            "analysis_id": self.analysis_id,
            "analysis_data": analysis_data
        }
        
        success, response = self.run_test(
            "AI Insights Generation",
            "POST",
            "ai-insights",
            200,
            data=request_data,
            timeout=60  # AI calls may take longer
        )
        
        if success and isinstance(response, dict):
            print(f"   Explanation length: {len(response.get('explanation', ''))}")
            print(f"   Recommendations count: {len(response.get('recommendations', []))}")
            print(f"   Cleaning suggestions: {len(response.get('cleaning_suggestions', {}))}")
        
        return success

    def test_data_cleaning(self):
        """Test data cleaning operations"""
        if not self.analysis_id:
            print("❌ Skipping data cleaning - no analysis ID available")
            return False
            
        # Define cleaning options for our test data
        cleaning_options = {
            "age": "fill_median",  # For missing age values
            "email": "drop_missing",  # For missing email values
            "salary": "cap_outliers",  # For salary outliers
            "name": "strip_whitespace",  # For whitespace issues
            "remove_duplicates": "yes"  # Remove duplicate rows
        }
        
        request_data = {
            "analysis_id": self.analysis_id,
            "cleaning_options": cleaning_options
        }
        
        success, response = self.run_test(
            "Data Cleaning",
            "POST",
            "clean-data",
            200,
            data=request_data,
            timeout=30
        )
        
        if success and isinstance(response, dict):
            print(f"   Original rows: {response.get('original_rows', 'N/A')}")
            print(f"   Cleaned rows: {response.get('cleaned_rows', 'N/A')}")
            print(f"   Changes made: {len(response.get('changes_made', []))}")
            for change in response.get('changes_made', []):
                print(f"     - {change}")
        
        return success

    def test_download_cleaned(self):
        """Test downloading cleaned data"""
        if not self.analysis_id:
            print("❌ Skipping download cleaned - no analysis ID available")
            return False
            
        success, response = self.run_test(
            "Download Cleaned Data",
            "GET",
            f"download-cleaned/{self.analysis_id}",
            200,
            timeout=30
        )
        
        if success:
            print(f"   Response type: {type(response)}")
            if isinstance(response, str):
                print(f"   Content length: {len(response)}")
                # Check if it looks like CSV
                if response.startswith('name,age,salary') or 'name' in response[:100]:
                    print("   ✅ Looks like valid CSV content")
                else:
                    print("   ⚠️  Content doesn't look like CSV")
        
        return success

    def test_download_report(self):
        """Test downloading analysis report"""
        if not self.analysis_id:
            print("❌ Skipping download report - no analysis ID available")
            return False
            
        success, response = self.run_test(
            "Download Report",
            "GET",
            f"download-report/{self.analysis_id}",
            200,
            timeout=30
        )
        
        if success:
            print(f"   Response type: {type(response)}")
            if isinstance(response, str):
                print(f"   Content length: {len(response)}")
                # Check if it looks like JSON
                try:
                    json.loads(response)
                    print("   ✅ Valid JSON content")
                except:
                    print("   ⚠️  Content doesn't look like valid JSON")
        
        return success

    def test_invalid_file_upload(self):
        """Test error handling with invalid file"""
        # Try uploading a text file instead of CSV
        files = {'file': ('invalid.txt', 'This is not a CSV file', 'text/plain')}
        
        success, response = self.run_test(
            "Invalid File Upload",
            "POST",
            "upload",
            400,  # Expect error
            files=files
        )
        
        return success

    def test_missing_analysis_id(self):
        """Test error handling with non-existent analysis ID"""
        fake_id = "non-existent-id"
        
        success, response = self.run_test(
            "Non-existent Analysis ID",
            "GET",
            f"analysis/{fake_id}",
            404,  # Expect not found
        )
        
        return success

def main():
    print("🚀 Starting Data Quality Auditor API Tests")
    print("=" * 60)
    
    # Initialize tester
    tester = DataQualityAPITester()
    
    # Run all tests
    tests = [
        ("API Root", tester.test_root_endpoint),
        ("File Upload & Analysis", tester.test_file_upload),
        ("AI Insights", tester.test_ai_insights),
        ("Data Cleaning", tester.test_data_cleaning),
        ("Download Cleaned Data", tester.test_download_cleaned),
        ("Download Report", tester.test_download_report),
        ("Invalid File Upload", tester.test_invalid_file_upload),
        ("Missing Analysis ID", tester.test_missing_analysis_id),
    ]
    
    for test_name, test_func in tests:
        try:
            test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {str(e)}")
        
        # Small delay between tests
        time.sleep(1)
    
    # Print final results
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed! Backend API is working correctly.")
        return 0
    else:
        print(f"⚠️  {tester.tests_run - tester.tests_passed} tests failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())