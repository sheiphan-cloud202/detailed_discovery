#!/usr/bin/env python3
"""
Test script to verify all three report generators work with centralized Bedrock config
"""

import sys
from pathlib import Path

def test_all_reports():
    """Test all three report generators"""
    print("=" * 70)
    print("🧪 Testing All Report Generators with Centralized Bedrock Config")
    print("=" * 70)
    
    try:
        from src.report_labs_executive import Cloud202ExecutiveReportGenerator
        
        print("\n📝 Generating all reports using test_json_comprehensive.json...")
        results = Cloud202ExecutiveReportGenerator.generate_all_reports(
            'test_json_comprehensive.json', 
            force_compliance=True
        )
        
        print("\n" + "=" * 70)
        print("✅ REPORT GENERATION RESULTS")
        print("=" * 70)
        
        # Check Executive Report
        exec_result = results.get('executive', {})
        if exec_result and exec_result.get('pdf_path'):
            print(f"✅ Executive Report: {exec_result['pdf_path']}")
        else:
            print("❌ Executive Report: FAILED")
            
        # Check Technical Report
        tech_result = results.get('technical', {})
        if tech_result and tech_result.get('pdf_path'):
            print(f"✅ Technical Report: {tech_result['pdf_path']}")
        else:
            print("❌ Technical Report: FAILED")
            
        # Check Compliance Report
        comp_result = results.get('compliance', {})
        if comp_result and comp_result.get('pdf_path'):
            print(f"✅ Compliance Report: {comp_result['pdf_path']}")
        else:
            print("❌ Compliance Report: FAILED")
        
        print("=" * 70)
        
        # Check if all succeeded
        all_success = all([
            exec_result and exec_result.get('pdf_path'),
            tech_result and tech_result.get('pdf_path'),
            comp_result and comp_result.get('pdf_path')
        ])
        
        if all_success:
            print("\n🎉 ALL REPORTS GENERATED SUCCESSFULLY!")
            return 0
        else:
            print("\n⚠️  Some reports failed to generate")
            return 1
            
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(test_all_reports())

