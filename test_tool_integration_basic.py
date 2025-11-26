#!/usr/bin/env python3
"""
Basic test for tool integration functionality without heavy dependencies.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test that we can import the core tool integration classes"""
    try:
        from council.tool_integration import (
            ToolCapability, 
            ToolPermission, 
            ToolCategory, 
            ToolCapabilityLevel,
            ToolResult,
            ToolUsageMetrics
        )
        print("✓ Core tool integration classes imported successfully")
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False

def test_tool_permission():
    """Test ToolPermission creation"""
    try:
        from council.tool_integration import ToolPermission, ToolCategory, ToolCapabilityLevel
        
        perm = ToolPermission(
            tool_name="test_tool",
            category=ToolCategory.FILE_SYSTEM,
            capability_level=ToolCapabilityLevel.READ_ONLY,
            rate_limit_per_minute=30
        )
        
        assert perm.tool_name == "test_tool"
        assert perm.category == ToolCategory.FILE_SYSTEM
        assert perm.capability_level == ToolCapabilityLevel.READ_ONLY
        assert perm.rate_limit_per_minute == 30
        
        print("✓ ToolPermission creation works correctly")
        return True
    except Exception as e:
        print(f"✗ ToolPermission test failed: {e}")
        return False

def test_tool_result():
    """Test ToolResult creation and serialization"""
    try:
        from council.tool_integration import ToolResult
        
        result = ToolResult(
            tool_name="test_tool",
            success=True,
            result={"data": "test"},
            execution_time=1.5
        )
        
        assert result.tool_name == "test_tool"
        assert result.success == True
        assert result.result == {"data": "test"}
        assert result.execution_time == 1.5
        
        # Test serialization
        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert result_dict["tool_name"] == "test_tool"
        assert result_dict["success"] == True
        
        print("✓ ToolResult creation and serialization works correctly")
        return True
    except Exception as e:
        print(f"✗ ToolResult test failed: {e}")
        return False

def test_tool_capability_basic():
    """Test basic ToolCapability functionality"""
    try:
        from council.tool_integration import ToolCapability, ToolPermission, ToolCategory, ToolCapabilityLevel
        
        # Create a test tool capability
        capability = ToolCapability("test_persona", "Test Persona")
        
        # Test permission management
        perm = ToolPermission(
            "filesystem_read",
            ToolCategory.FILE_SYSTEM,
            ToolCapabilityLevel.READ_ONLY,
            rate_limit_per_minute=10
        )
        
        capability.add_tool_permission(perm)
        
        # Test rate limiting
        assert capability.check_rate_limit("filesystem_read") == True
        
        # Test permission check
        assert "filesystem_read" in capability.tool_permissions
        
        print("✓ ToolCapability basic functionality works correctly")
        return True
    except Exception as e:
        print(f"✗ ToolCapability test failed: {e}")
        return False

def test_enhanced_persona():
    """Test EnhancedPersona without dependencies"""
    try:
        from council.tool_integration import EnhancedPersona
        
        persona = EnhancedPersona(
            persona_id="test_analyst",
            persona_name="Test Analyst", 
            expertise_domains=["analysis", "testing"]
        )
        
        assert persona.persona_id == "test_analyst"
        assert persona.persona_name == "Test Analyst"
        assert "analysis" in persona.expertise_domains
        
        print("✓ EnhancedPersona creation works correctly")
        return True
    except Exception as e:
        print(f"✗ EnhancedPersona test failed: {e}")
        return False

def main():
    """Run all basic tests"""
    print("Running basic tool integration tests...")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_tool_permission,
        test_tool_result,
        test_tool_capability_basic,
        test_enhanced_persona
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        if test():
            passed += 1
        else:
            failed += 1
        print()
    
    print("=" * 50)
    print(f"Tests completed: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All basic tests passed!")
        return True
    else:
        print(f"❌ {failed} tests failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)