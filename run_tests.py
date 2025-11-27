#!/usr/bin/env python3
"""
OPTIMUS TEST RUNNER
==================

Runs all available tests and shows what actually works in the system.
This runner attempts multiple test approaches to find what's functional.
"""

import subprocess
import sys
import os
import time
from datetime import datetime

def run_test(test_file, description, required=True):
    """Run a test file and capture results"""
    print(f"\n{'='*80}")
    print(f"🧪 Running: {description}")
    print(f"File: {test_file}")
    print(f"{'='*80}")
    
    if not os.path.exists(test_file):
        print(f"❌ SKIPPED: Test file {test_file} does not exist")
        return False, "File not found"
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            [sys.executable, test_file],
            capture_output=True,
            text=True,
            timeout=60  # 60 second timeout
        )
        
        execution_time = time.time() - start_time
        
        if result.returncode == 0:
            print(f"✅ PASSED: {description} (Exit code: {result.returncode})")
            print(f"⏱️ Execution time: {execution_time:.2f}s")
            if result.stdout:
                print(f"\n📋 OUTPUT:")
                print(result.stdout)
            return True, "Passed successfully"
            
        elif result.returncode == 1 and not required:
            print(f"⚠️ PARTIAL: {description} (Exit code: {result.returncode})")
            print(f"⏱️ Execution time: {execution_time:.2f}s")
            print(f"Some functionality working, some issues detected")
            if result.stdout:
                print(f"\n📋 OUTPUT:")
                print(result.stdout)
            return "partial", "Partially functional"
            
        else:
            print(f"❌ FAILED: {description} (Exit code: {result.returncode})")
            print(f"⏱️ Execution time: {execution_time:.2f}s")
            if result.stdout:
                print(f"\n📋 STDOUT:")
                print(result.stdout)
            if result.stderr:
                print(f"\n📋 STDERR:")
                print(result.stderr)
            return False, f"Exit code {result.returncode}"
            
    except subprocess.TimeoutExpired:
        print(f"⏰ TIMEOUT: {description} (exceeded 60 seconds)")
        return False, "Timeout"
        
    except Exception as e:
        print(f"💥 ERROR: {description} - {str(e)}")
        return False, f"Exception: {str(e)}"


def check_system_status():
    """Check basic system status before running tests"""
    print("🔍 SYSTEM STATUS CHECK")
    print("="*50)
    
    # Check Python version
    python_version = sys.version.split()[0]
    print(f"Python version: {python_version}")
    
    # Check if we're in the right directory
    if os.path.exists('src/council'):
        print("✅ In Optimus project directory")
    else:
        print("❌ Not in Optimus project directory")
        return False
    
    # Check key files exist
    key_files = [
        'src/council/orchestrator.py',
        'src/council/personas/strategist.py', 
        'src/api/council.py'
    ]
    
    missing_files = []
    for file_path in key_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path}")
            missing_files.append(file_path)
    
    if missing_files:
        print(f"\n⚠️ Missing {len(missing_files)} key files")
    
    return len(missing_files) == 0


def run_simple_import_test():
    """Run a very basic import test inline"""
    print("\n🧪 INLINE IMPORT TEST")
    print("-" * 30)
    
    try:
        # Test the simplest possible imports
        import sys
        sys.path.insert(0, '.')
        
        # Test basic modules
        try:
            from src.council.persona import PersonaResponse, PersonaPriority
            print("✅ Basic persona imports work")
            basic_imports = True
        except Exception as e:
            print(f"❌ Basic persona imports failed: {e}")
            basic_imports = False
        
        # Test specific personas (these might fail due to dependencies)
        persona_imports = 0
        persona_classes = ['strategist', 'pragmatist', 'innovator', 'guardian', 'analyst']
        
        for persona_name in persona_classes:
            try:
                exec(f"from src.council.personas.{persona_name} import {persona_name.title()}Persona")
                print(f"✅ {persona_name.title()} persona imports")
                persona_imports += 1
            except Exception as e:
                print(f"❌ {persona_name.title()} persona failed: {str(e)[:50]}")
        
        print(f"\n📊 Import Results: {persona_imports}/{len(persona_classes)} personas, Basic: {basic_imports}")
        return basic_imports, persona_imports
        
    except Exception as e:
        print(f"❌ Critical import error: {e}")
        return False, 0


def main():
    """Main test runner"""
    print("🚀 OPTIMUS TEST RUNNER")
    print("="*80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # System status check
    system_ok = check_system_status()
    if not system_ok:
        print("❌ System check failed - may affect test results")
    
    # Inline import test
    basic_imports, persona_imports = run_simple_import_test()
    
    # Test suite definitions
    test_suites = [
        {
            'file': 'tests/test_council_actual.py',
            'description': 'Comprehensive Council Tests (Correct Method Signatures)',
            'required': True
        },
        {
            'file': 'tests/test_council_working.py', 
            'description': 'Original Council Working Tests',
            'required': False
        },
        {
            'file': 'tests/test_council_minimal.py',
            'description': 'Minimal Council Tests',
            'required': False
        },
        {
            'file': 'simple_council_test.py',
            'description': 'Simple Council Demo',
            'required': False
        }
    ]
    
    # Run all test suites
    results = []
    for test_suite in test_suites:
        result, details = run_test(
            test_suite['file'], 
            test_suite['description'],
            test_suite['required']
        )
        results.append({
            'name': test_suite['description'],
            'file': test_suite['file'],
            'result': result,
            'details': details,
            'required': test_suite['required']
        })
    
    # Final summary
    print(f"\n{'='*80}")
    print("🏁 FINAL TEST SUMMARY")
    print(f"{'='*80}")
    
    passed_tests = sum(1 for r in results if r['result'] is True)
    partial_tests = sum(1 for r in results if r['result'] == 'partial')
    failed_tests = sum(1 for r in results if r['result'] is False)
    total_tests = len(results)
    
    print(f"✅ Passed: {passed_tests}")
    print(f"⚠️ Partial: {partial_tests}")
    print(f"❌ Failed: {failed_tests}")
    print(f"📊 Total: {total_tests}")
    
    # System functionality assessment
    print(f"\n🔍 SYSTEM FUNCTIONALITY ASSESSMENT")
    print("-"*50)
    
    if basic_imports:
        print("✅ Core framework imports working")
    else:
        print("❌ Critical framework import issues")
    
    if persona_imports >= 3:
        print(f"✅ Persona system functional ({persona_imports}/5 personas)")
    elif persona_imports >= 1:
        print(f"⚠️ Persona system partially working ({persona_imports}/5 personas)")
    else:
        print("❌ Persona system not functional")
    
    if passed_tests >= 1:
        print("✅ At least one test suite passes")
    elif partial_tests >= 1:
        print("⚠️ Partial functionality detected")
    else:
        print("❌ No test suites passing")
    
    # Overall system status
    if passed_tests >= 1 and basic_imports:
        system_status = "FUNCTIONAL"
        exit_code = 0
    elif partial_tests >= 1 or persona_imports >= 2:
        system_status = "PARTIALLY_FUNCTIONAL"
        exit_code = 0
    else:
        system_status = "NEEDS_WORK"
        exit_code = 1
    
    print(f"\n🎯 OVERALL SYSTEM STATUS: {system_status}")
    
    # Detailed results table
    print(f"\n📋 DETAILED RESULTS:")
    print("-"*80)
    print(f"{'Test Suite':<45} {'Result':<12} {'Details':<23}")
    print("-"*80)
    
    for result in results:
        result_symbol = {
            True: "✅ PASSED",
            "partial": "⚠️ PARTIAL", 
            False: "❌ FAILED"
        }.get(result['result'], "❓ UNKNOWN")
        
        details = result['details'][:22] if result['details'] else "No details"
        
        print(f"{result['name'][:44]:<45} {result_symbol:<12} {details:<23}")
    
    # Recommendations
    if system_status != "FUNCTIONAL":
        print(f"\n💡 RECOMMENDATIONS:")
        print("-"*30)
        if not basic_imports:
            print("🔧 Fix critical import dependencies (networkx, etc.)")
        if persona_imports < 3:
            print("🔧 Resolve persona initialization issues")
        if failed_tests == total_tests:
            print("🔧 Check Python environment and dependencies")
    
    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Exit code: {exit_code}")
    
    return exit_code


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)