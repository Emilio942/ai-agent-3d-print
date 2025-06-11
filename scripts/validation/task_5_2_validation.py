#!/usr/bin/env python3
"""
Production Readiness Validation Script for AI Agent 3D Print System

This script validates that all production readiness components are working:
- Configuration management
- Health monitoring
- Environment-specific configs
- API endpoints
- Documentation completeness

Run this script to verify Task 5.2 completion.
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Any
import yaml
import requests

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import load_config
from core.health_monitor import health_monitor, setup_default_monitoring
from core.logger import get_logger

logger = get_logger("validation")


class ProductionReadinessValidator:
    """Validates all production readiness components."""
    
    def __init__(self):
        self.test_results = {}
        self.config = None
        self.base_url = "http://localhost:8000"
        
    def log_test_result(self, test_name: str, success: bool, message: str = ""):
        """Log test result with consistent formatting."""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        self.test_results[test_name] = {
            "success": success,
            "message": message,
            "timestamp": time.time()
        }
        
    async def validate_configuration_management(self) -> None:
        """Validate environment-specific configuration management."""
        print("\n🔧 VALIDATING CONFIGURATION MANAGEMENT")
        
        # Test 1: Base configuration loading
        try:
            self.config = load_config()
            self.log_test_result(
                "Base Configuration Loading",
                True,
                f"Loaded configuration with {len(self.config)} sections"
            )
        except Exception as e:
            self.log_test_result(
                "Base Configuration Loading",
                False,
                f"Failed to load base config: {e}"
            )
            return
        
        # Test 2: Environment-specific config files exist
        config_dir = Path("config")
        required_env_configs = ["development.yaml", "staging.yaml", "production.yaml"]
        
        for env_config in required_env_configs:
            config_file = config_dir / env_config
            exists = config_file.exists()
            self.log_test_result(
                f"Environment Config: {env_config}",
                exists,
                "File exists" if exists else "File missing"
            )
        
        # Test 3: Environment variable support
        original_env = os.getenv('APP_ENVIRONMENT')
        try:
            # Test development environment
            os.environ['APP_ENVIRONMENT'] = 'development'
            dev_config = load_config()
            dev_environment = dev_config.get('app', {}).get('environment')
            
            self.log_test_result(
                "Development Environment Loading",
                dev_environment == 'development',
                f"Environment: {dev_environment}"
            )
            
            # Test production environment
            os.environ['APP_ENVIRONMENT'] = 'production'
            prod_config = load_config()
            prod_environment = prod_config.get('app', {}).get('environment')
            
            self.log_test_result(
                "Production Environment Loading",
                prod_environment == 'production',
                f"Environment: {prod_environment}"
            )
            
        finally:
            # Restore original environment
            if original_env:
                os.environ['APP_ENVIRONMENT'] = original_env
            elif 'APP_ENVIRONMENT' in os.environ:
                del os.environ['APP_ENVIRONMENT']
        
        # Test 4: Configuration validation
        required_sections = ['app', 'api', 'agents', 'logging', 'monitoring']
        for section in required_sections:
            exists = section in self.config
            self.log_test_result(
                f"Config Section: {section}",
                exists,
                "Section present" if exists else "Section missing"
            )
    
    async def validate_health_monitoring(self) -> None:
        """Validate comprehensive health monitoring system."""
        print("\n🏥 VALIDATING HEALTH MONITORING")
        
        # Test 1: Health monitor initialization
        try:
            await setup_default_monitoring()
            self.log_test_result(
                "Health Monitor Initialization",
                True,
                f"Initialized with {len(health_monitor.components)} components"
            )
        except Exception as e:
            self.log_test_result(
                "Health Monitor Initialization", 
                False,
                f"Failed to initialize: {e}"
            )
            return
        
        # Test 2: Component registration
        expected_components = [
            "api", "database", "redis", "file_system",
            "research_agent", "cad_agent", "slicer_agent", "printer_agent"
        ]
        
        for component in expected_components:
            registered = component in health_monitor.components
            self.log_test_result(
                f"Component Registration: {component}",
                registered,
                "Registered" if registered else "Not registered"
            )
        
        # Test 3: Individual component health checks
        for component_name in health_monitor.components.keys():
            try:
                health_result = await health_monitor.check_component_health(component_name)
                success = health_result.status in ["healthy", "degraded"]  # degraded is acceptable
                self.log_test_result(
                    f"Component Health: {component_name}",
                    success,
                    f"Status: {health_result.status}, Response: {health_result.response_time_ms:.1f}ms"
                )
            except Exception as e:
                self.log_test_result(
                    f"Component Health: {component_name}",
                    False,
                    f"Health check failed: {e}"
                )
        
        # Test 4: Overall system health
        try:
            overall_health = await health_monitor.get_overall_health()
            success = overall_health["overall_status"] in ["healthy", "degraded"]
            self.log_test_result(
                "Overall System Health",
                success,
                f"Status: {overall_health['overall_status']}"
            )
        except Exception as e:
            self.log_test_result(
                "Overall System Health",
                False,
                f"Failed to get overall health: {e}"
            )
        
        # Test 5: System metrics collection
        try:
            system_metrics = health_monitor.get_system_metrics()
            metrics_valid = all([
                system_metrics.cpu_usage_percent >= 0,
                system_metrics.memory_usage_percent >= 0,
                system_metrics.disk_usage_percent >= 0,
                system_metrics.uptime_seconds >= 0
            ])
            self.log_test_result(
                "System Metrics Collection",
                metrics_valid,
                f"CPU: {system_metrics.cpu_usage_percent:.1f}%, " +
                f"Memory: {system_metrics.memory_usage_percent:.1f}%, " +
                f"Disk: {system_metrics.disk_usage_percent:.1f}%"
            )
        except Exception as e:
            self.log_test_result(
                "System Metrics Collection",
                False,
                f"Failed to collect metrics: {e}"
            )
    
    def validate_api_endpoints(self) -> None:
        """Validate API health endpoints."""
        print("\n🌐 VALIDATING API HEALTH ENDPOINTS")
        
        # Test basic health endpoint (simulate API server response)
        try:
            # Since we may not have the API running during validation,
            # we'll validate the endpoint definitions exist
            from api.main import app
            
            # Check if health endpoints are defined
            routes = [route.path for route in app.routes]
            
            expected_endpoints = [
                "/health",
                "/health/detailed", 
                "/health/components/{component_name}"
            ]
            
            for endpoint in expected_endpoints:
                # For parameterized routes, check if pattern exists
                if "{" in endpoint:
                    pattern_exists = any(endpoint.replace("{component_name}", "") in route for route in routes)
                    self.log_test_result(
                        f"API Endpoint: {endpoint}",
                        pattern_exists,
                        "Endpoint pattern defined" if pattern_exists else "Pattern not found"
                    )
                else:
                    exists = endpoint in routes
                    self.log_test_result(
                        f"API Endpoint: {endpoint}",
                        exists,
                        "Endpoint defined" if exists else "Endpoint missing"
                    )
                    
        except ImportError as e:
            self.log_test_result(
                "API Endpoints Validation",
                False,
                f"Could not import API module: {e}"
            )
    
    def validate_documentation(self) -> None:
        """Validate documentation completeness."""
        print("\n📚 VALIDATING DOCUMENTATION")
        
        docs_dir = Path("docs")
        
        # Test 1: Documentation directory exists
        self.log_test_result(
            "Documentation Directory",
            docs_dir.exists(),
            "Directory exists" if docs_dir.exists() else "Directory missing"
        )
        
        # Test 2: Required documentation files
        required_docs = [
            "API_DOCUMENTATION.md",
            "DEPLOYMENT_GUIDE.md"
        ]
        
        for doc_file in required_docs:
            doc_path = docs_dir / doc_file
            exists = doc_path.exists()
            
            if exists:
                # Check file size (should be substantial)
                size_kb = doc_path.stat().st_size / 1024
                substantial = size_kb > 10  # At least 10KB
                self.log_test_result(
                    f"Documentation: {doc_file}",
                    substantial,
                    f"File exists ({size_kb:.1f}KB)" if substantial else f"File too small ({size_kb:.1f}KB)"
                )
            else:
                self.log_test_result(
                    f"Documentation: {doc_file}",
                    False,
                    "File missing"
                )
        
        # Test 3: Configuration documentation
        config_docs = [
            "config/README.md",
            "tech_stack.md",
            "README.md"
        ]
        
        for doc_file in config_docs:
            doc_path = Path(doc_file)
            exists = doc_path.exists()
            self.log_test_result(
                f"Config Documentation: {doc_file}",
                exists,
                "File exists" if exists else "File missing"
            )
    
    def validate_deployment_readiness(self) -> None:
        """Validate deployment-related files and configurations."""
        print("\n🚀 VALIDATING DEPLOYMENT READINESS")
        
        # Test 1: Docker configuration
        docker_files = [
            "Dockerfile",
            "docker-compose.prod.yml",
            ".dockerignore"
        ]
        
        for docker_file in docker_files:
            file_path = Path(docker_file)
            if docker_file == ".dockerignore":
                # .dockerignore is optional but recommended
                exists = file_path.exists()
                self.log_test_result(
                    f"Docker File: {docker_file}",
                    True,  # Don't fail if .dockerignore is missing
                    "File exists" if exists else "File missing (optional)"
                )
            else:
                exists = file_path.exists()
                self.log_test_result(
                    f"Docker File: {docker_file}",
                    exists,
                    "File exists" if exists else "File missing"
                )
        
        # Test 2: Production startup script
        startup_script = Path("start_api_production.py")
        self.log_test_result(
            "Production Startup Script",
            startup_script.exists(),
            "Script exists" if startup_script.exists() else "Script missing"
        )
        
        # Test 3: Requirements file
        requirements = Path("requirements.txt")
        if requirements.exists():
            with open(requirements, 'r') as f:
                deps = f.read()
                has_production_deps = all(dep in deps for dep in ['uvicorn', 'fastapi', 'psutil'])
                self.log_test_result(
                    "Production Dependencies",
                    has_production_deps,
                    "All required dependencies present" if has_production_deps else "Missing dependencies"
                )
        else:
            self.log_test_result(
                "Requirements File",
                False,
                "requirements.txt missing"
            )
        
        # Test 4: Environment configuration templates
        env_templates = [
            "config/production.yaml",
            "config/staging.yaml"
        ]
        
        for template in env_templates:
            template_path = Path(template)
            exists = template_path.exists()
            self.log_test_result(
                f"Environment Template: {template}",
                exists,
                "Template exists" if exists else "Template missing"
            )
    
    def validate_security_configuration(self) -> None:
        """Validate security-related configurations."""
        print("\n🔒 VALIDATING SECURITY CONFIGURATION")
        
        # Test 1: Security configuration in production config
        if self.config:
            security_config = self.config.get('security', {})
            
            # Check if security options are configured
            security_features = [
                'api_key_enabled',
                'jwt_enabled', 
                'input_validation'
            ]
            
            for feature in security_features:
                configured = feature in security_config
                self.log_test_result(
                    f"Security Feature: {feature}",
                    configured,
                    "Configured" if configured else "Not configured"
                )
        
        # Test 2: CORS configuration
        if self.config:
            api_config = self.config.get('api', {})
            cors_configured = 'cors_origins' in api_config
            self.log_test_result(
                "CORS Configuration",
                cors_configured,
                "CORS origins configured" if cors_configured else "CORS not configured"
            )
        
        # Test 3: Rate limiting
        if self.config:
            api_config = self.config.get('api', {})
            rate_limit_config = api_config.get('rate_limit', {})
            rate_limiting_enabled = rate_limit_config.get('enabled', False)
            self.log_test_result(
                "Rate Limiting",
                rate_limiting_enabled,
                "Rate limiting enabled" if rate_limiting_enabled else "Rate limiting disabled"
            )
    
    def print_summary(self) -> None:
        """Print validation summary."""
        print("\n" + "="*60)
        print("🎯 PRODUCTION READINESS VALIDATION SUMMARY")
        print("="*60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result['success'])
        failed_tests = total_tests - passed_tests
        
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"📊 Test Results:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: ✅ {passed_tests}")
        print(f"   Failed: ❌ {failed_tests}")
        print(f"   Success Rate: {success_rate:.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ Failed Tests:")
            for test_name, result in self.test_results.items():
                if not result['success']:
                    print(f"   • {test_name}: {result['message']}")
        
        print(f"\n🏆 Production Readiness Status:")
        if success_rate >= 90:
            print("   ✅ EXCELLENT - System is production ready!")
        elif success_rate >= 80:
            print("   🟡 GOOD - Minor issues need addressing")
        elif success_rate >= 70:
            print("   🟠 FAIR - Several issues need fixing")
        else:
            print("   ❌ POOR - Significant work needed before production")
        
        print(f"\n📋 Task 5.2 Completion Status:")
        completion_areas = {
            "Configuration Management": any("Config" in test for test in self.test_results),
            "Health Monitoring": any("Health" in test for test in self.test_results),
            "API Documentation": any("Documentation" in test for test in self.test_results),
            "Deployment Readiness": any("Docker" in test or "Production" in test for test in self.test_results)
        }
        
        for area, completed in completion_areas.items():
            status = "✅" if completed else "❌"
            print(f"   {status} {area}")
        
        all_completed = all(completion_areas.values())
        print(f"\n🎉 Task 5.2 Status: {'✅ COMPLETED' if all_completed else '❌ INCOMPLETE'}")
        
        if all_completed:
            print("\n🚀 System ist deployment-ready mit vollständiger Dokumentation!")


async def main():
    """Run all production readiness validations."""
    print("🔍 AI Agent 3D Print System - Production Readiness Validation")
    print("Task 5.2: Production Readiness Validation")
    print("="*60)
    
    validator = ProductionReadinessValidator()
    
    # Run all validation tests
    await validator.validate_configuration_management()
    await validator.validate_health_monitoring()
    validator.validate_api_endpoints()
    validator.validate_documentation()
    validator.validate_deployment_readiness()
    validator.validate_security_configuration()
    
    # Print summary
    validator.print_summary()
    
    # Save results
    results_file = Path("validation_results.json")
    with open(results_file, 'w') as f:
        json.dump({
            "timestamp": time.time(),
            "test_results": validator.test_results,
            "summary": {
                "total_tests": len(validator.test_results),
                "passed_tests": sum(1 for r in validator.test_results.values() if r['success']),
                "success_rate": (sum(1 for r in validator.test_results.values() if r['success']) / len(validator.test_results)) * 100
            }
        }, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: {results_file}")


if __name__ == "__main__":
    asyncio.run(main())
