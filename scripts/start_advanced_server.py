#!/usr/bin/env python3
"""
AI Agent 3D Print System - Advanced Features Production Server

This script starts the production-ready FastAPI server with all advanced features:
- Multi-Material Support
- AI-Enhanced Design Analysis
- 3D Print Preview System
- Historical Data & Learning
- Advanced Analytics Dashboard

Usage:
    python start_advanced_server.py [--port PORT] [--host HOST] [--dev]
"""

import argparse
import sys
import uvicorn
from pathlib import Path

def main():
    """Start the AI Agent 3D Print System with Advanced Features"""
    
    parser = argparse.ArgumentParser(
        description="AI Agent 3D Print System - Advanced Features Server"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=8000, 
        help="Port to run the server on (default: 8000)"
    )
    parser.add_argument(
        "--host", 
        type=str, 
        default="0.0.0.0", 
        help="Host to bind the server to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--dev", 
        action="store_true", 
        help="Run in development mode with auto-reload"
    )
    parser.add_argument(
        "--log-level", 
        type=str, 
        default="info", 
        choices=["debug", "info", "warning", "error"],
        help="Log level (default: info)"
    )
    
    args = parser.parse_args()
    
    print("🚀 AI Agent 3D Print System - Advanced Features Server")
    print("=" * 60)
    print("🔧 Advanced Features Enabled:")
    print("  ✅ Multi-Material Support")
    print("  ✅ AI-Enhanced Design Analysis") 
    print("  ✅ 3D Print Preview System")
    print("  ✅ Historical Data & Learning")
    print("  ✅ Performance Analytics")
    print("  ✅ Advanced Dashboard Interface")
    print("")
    print(f"🌐 Server Configuration:")
    print(f"  📍 Host: {args.host}")
    print(f"  🔌 Port: {args.port}")
    print(f"  🔧 Mode: {'Development' if args.dev else 'Production'}")
    print(f"  📝 Log Level: {args.log_level.upper()}")
    print("")
    print("📱 Access URLs:")
    print(f"  🏠 Main Dashboard: http://localhost:{args.port}/templates/advanced_dashboard.html")
    print(f"  🎨 3D Preview: http://localhost:{args.port}/templates/preview.html")
    print(f"  📚 API Docs: http://localhost:{args.port}/docs")
    print(f"  🔍 Health Check: http://localhost:{args.port}/health")
    print("")
    
    try:
        # Validate that we're in the correct directory
        if not Path("api/main.py").exists():
            print("❌ Error: Please run this script from the project root directory")
            print("   Expected to find: api/main.py")
            sys.exit(1)
        
        print("🚀 Starting server...")
        print("   Press Ctrl+C to stop")
        print("=" * 60)
        
        # Start the server
        uvicorn.run(
            "api.main:app",
            host=args.host,
            port=args.port,
            reload=args.dev,
            log_level=args.log_level,
            access_log=True,
            reload_dirs=["api", "core", "templates", "static"] if args.dev else None
        )
        
    except KeyboardInterrupt:
        print("\n" + "=" * 60)
        print("🛑 Server stopped by user")
        print("👋 Thank you for using AI Agent 3D Print System!")
    except Exception as e:
        print(f"\n❌ Server startup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
