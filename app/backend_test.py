import requests
import sys
import json
from datetime import datetime, timedelta

class MarketingCalendarAPITester:
    def __init__(self, base_url="https://marketing-planner-2.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.created_campaigns = []

    def run_test(self, name, method, endpoint, expected_status, data=None, params=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    if method == 'GET' and 'campaigns' in endpoint:
                        print(f"   Response: Found {len(response_data) if isinstance(response_data, list) else 1} campaigns")
                    elif method == 'POST' and 'campaigns' in endpoint:
                        print(f"   Created campaign ID: {response_data.get('id', 'N/A')}")
                    elif 'stats' in endpoint:
                        print(f"   Stats: {response_data}")
                    return True, response_data
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test root API endpoint"""
        return self.run_test("Root API", "GET", "", 200)

    def test_get_stats(self):
        """Test stats endpoint"""
        success, data = self.run_test("Get Stats", "GET", "stats", 200)
        if success and data:
            required_keys = ['total', 'by_status', 'by_channel']
            for key in required_keys:
                if key not in data:
                    print(f"❌ Missing key in stats: {key}")
                    return False
            print(f"   Total campaigns: {data.get('total', 0)}")
        return success

    def test_get_templates(self):
        """Test templates endpoint"""
        success, data = self.run_test("Get Templates", "GET", "templates", 200)
        if success and data:
            print(f"   Found {len(data)} templates")
            if len(data) > 0:
                template = data[0]
                required_keys = ['id', 'name', 'description', 'channel', 'default_content']
                for key in required_keys:
                    if key not in template:
                        print(f"❌ Missing key in template: {key}")
                        return False
        return success

    def test_create_campaign(self, title_suffix=""):
        """Test campaign creation"""
        campaign_data = {
            "title": f"Test Campaign {title_suffix}",
            "description": "Test campaign description",
            "channel": "social",
            "status": "draft",
            "date": (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'),
            "time": "10:00"
        }
        
        success, data = self.run_test("Create Campaign", "POST", "campaigns", 200, campaign_data)
        if success and data:
            campaign_id = data.get('id')
            if campaign_id:
                self.created_campaigns.append(campaign_id)
                # Verify color assignment
                expected_color = "#FF6B6B"  # social channel color
                if data.get('color') != expected_color:
                    print(f"❌ Color mismatch - Expected {expected_color}, got {data.get('color')}")
                    return False, None
                return True, campaign_id
        return False, None

    def test_get_campaigns(self):
        """Test getting all campaigns"""
        return self.run_test("Get All Campaigns", "GET", "campaigns", 200)

    def test_get_single_campaign(self, campaign_id):
        """Test getting a single campaign"""
        return self.run_test(f"Get Campaign {campaign_id}", "GET", f"campaigns/{campaign_id}", 200)

    def test_update_campaign(self, campaign_id):
        """Test updating a campaign"""
        update_data = {
            "title": "Updated Test Campaign",
            "channel": "email",
            "status": "scheduled"
        }
        
        success, data = self.run_test(f"Update Campaign {campaign_id}", "PUT", f"campaigns/{campaign_id}", 200, update_data)
        if success and data:
            # Verify color updated for new channel
            expected_color = "#4ECDC4"  # email channel color
            if data.get('color') != expected_color:
                print(f"❌ Color not updated - Expected {expected_color}, got {data.get('color')}")
                return False
        return success

    def test_delete_campaign(self, campaign_id):
        """Test deleting a campaign"""
        return self.run_test(f"Delete Campaign {campaign_id}", "DELETE", f"campaigns/{campaign_id}", 200)

    def test_get_nonexistent_campaign(self):
        """Test getting a non-existent campaign"""
        return self.run_test("Get Non-existent Campaign", "GET", "campaigns/nonexistent-id", 404)

    def test_update_nonexistent_campaign(self):
        """Test updating a non-existent campaign"""
        update_data = {"title": "Should fail"}
        return self.run_test("Update Non-existent Campaign", "PUT", "campaigns/nonexistent-id", 404, update_data)

    def test_delete_nonexistent_campaign(self):
        """Test deleting a non-existent campaign"""
        return self.run_test("Delete Non-existent Campaign", "DELETE", "campaigns/nonexistent-id", 404)

    def cleanup_campaigns(self):
        """Clean up created campaigns"""
        print(f"\n🧹 Cleaning up {len(self.created_campaigns)} test campaigns...")
        for campaign_id in self.created_campaigns:
            try:
                response = requests.delete(f"{self.api_url}/campaigns/{campaign_id}")
                if response.status_code == 200:
                    print(f"   ✅ Deleted campaign {campaign_id}")
                else:
                    print(f"   ❌ Failed to delete campaign {campaign_id}")
            except Exception as e:
                print(f"   ❌ Error deleting campaign {campaign_id}: {e}")

def main():
    print("🚀 Starting Marketing Calendar API Tests")
    print("=" * 50)
    
    tester = MarketingCalendarAPITester()
    
    try:
        # Test basic endpoints
        tester.test_root_endpoint()
        tester.test_get_stats()
        tester.test_get_templates()
        
        # Test campaign CRUD operations
        tester.test_get_campaigns()
        
        # Create test campaigns
        success1, campaign_id1 = tester.test_create_campaign("1")
        success2, campaign_id2 = tester.test_create_campaign("2")
        
        if campaign_id1:
            tester.test_get_single_campaign(campaign_id1)
            tester.test_update_campaign(campaign_id1)
            
        # Test error cases
        tester.test_get_nonexistent_campaign()
        tester.test_update_nonexistent_campaign()
        tester.test_delete_nonexistent_campaign()
        
        # Test stats after creating campaigns
        print("\n📊 Testing stats after campaign creation:")
        tester.test_get_stats()
        
        # Clean up test campaigns
        if campaign_id1:
            tester.test_delete_campaign(campaign_id1)
        if campaign_id2:
            tester.test_delete_campaign(campaign_id2)
            
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
    finally:
        # Ensure cleanup
        tester.cleanup_campaigns()
    
    # Print results
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {tester.tests_passed}/{tester.tests_run} passed")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        print(f"❌ {tester.tests_run - tester.tests_passed} tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())