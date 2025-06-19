#!/usr/bin/env python3
"""
Simple test script for the new API endpoints
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.voice_control import VoiceControlManager
from core.analytics_dashboard import AnalyticsDashboard
from core.template_library import TemplateLibrary

async def test_voice_control():
    """Test voice control functionality"""
    print("🎤 Testing Voice Control...")
    
    try:
        voice_manager = VoiceControlManager()
        
        # Test status
        status = await voice_manager.get_status()
        print(f"   Status: {status}")
        
        # Test text command processing
        command = await voice_manager.process_text_command("print a small gear")
        print(f"   Command result: {command}")
        
        print("✅ Voice Control test passed!")
        return True
    except Exception as e:
        print(f"❌ Voice Control test failed: {e}")
        return False

async def test_analytics():
    """Test analytics dashboard functionality"""
    print("📊 Testing Analytics Dashboard...")
    
    try:
        analytics = AnalyticsDashboard()
        
        # Test overview
        overview = await analytics.get_overview()
        print(f"   Overview: {overview}")
        
        # Test live metrics
        metrics = await analytics.get_live_metrics()
        print(f"   Live metrics: {metrics}")
        
        print("✅ Analytics Dashboard test passed!")
        return True
    except Exception as e:
        print(f"❌ Analytics Dashboard test failed: {e}")
        return False

async def test_templates():
    """Test template library functionality"""
    print("📋 Testing Template Library...")
    
    try:
        templates = TemplateLibrary()
        
        # Test template listing
        template_list = await templates.list_templates()
        print(f"   Templates found: {len(template_list)}")
        
        # Test categories
        categories = await templates.get_categories()
        print(f"   Categories: {len(categories)}")
        
        # Test search
        search_results = await templates.search_templates(category="mechanical")
        print(f"   Mechanical templates: {len(search_results)}")
        
        print("✅ Template Library test passed!")
        return True
    except Exception as e:
        print(f"❌ Template Library test failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("🚀 Testing New Features Integration\n")
    
    results = []
    
    # Test each component
    results.append(await test_voice_control())
    print()
    results.append(await test_analytics())
    print()
    results.append(await test_templates())
    
    print("\n" + "="*50)
    print("📋 TEST SUMMARY")
    print("="*50)
    
    if all(results):
        print("🎉 ALL TESTS PASSED!")
        print("The new features are ready for integration!")
    else:
        failed_count = len([r for r in results if not r])
        print(f"⚠️  {failed_count} tests failed")
        print("Please check the errors above")
    
    return all(results)

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
