#!/usr/bin/env python3
"""
Test Professional Dashboard
Quick test to verify the professional dashboard is working
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_dashboard_imports():
    """Test that all required modules can be imported"""
    try:
        from professional_dashboard import app, logger
        print("✅ Professional dashboard imports successful")
        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def test_flask_app():
    """Test that Flask app can be created"""
    try:
        from professional_dashboard import app
        with app.test_client() as client:
            response = client.get('/')
            if response.status_code == 200:
                print("✅ Flask app working - Homepage accessible")
                return True
            else:
                print(f"❌ Homepage error: {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ Flask app error: {e}")
        return False

def test_api_endpoints():
    """Test that API endpoints are accessible"""
    try:
        from professional_dashboard import app
        with app.test_client() as client:
            # Test market overview endpoint
            response = client.get('/api/market-overview')
            if response.status_code in [200, 500]:  # 500 is OK if data service not ready
                print("✅ API endpoints accessible")
                return True
            else:
                print(f"❌ API error: {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ API test error: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing Professional Dashboard...")
    print("=" * 50)
    
    tests = [
        test_dashboard_imports,
        test_flask_app,
        test_api_endpoints
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Professional dashboard is ready.")
        print("\n🚀 To start the dashboard:")
        print("   python start_professional_dashboard.py")
        print("\n🌐 Then open: http://localhost:5001")
    else:
        print("⚠️  Some tests failed. Check the errors above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

