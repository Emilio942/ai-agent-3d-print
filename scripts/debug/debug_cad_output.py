#!/usr/bin/env python3

import sys
import os
import asyncio
import json
from pathlib import Path

# Add project root to Python path  
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from agents.cad_agent import CADAgent

async def debug_cad_output():
    """Debug what the CAD agent outputs for a 2cm cube."""
    print("🔍 Debugging CAD Agent Output")
    print("=" * 50)
    
    # Initialize CAD agent
    cad_agent = CADAgent("debug_cad")
    
    # Execute the same task as in the workflow
    result = await cad_agent.execute_task({
        "task_id": "debug_cad",
        "operation": "create_primitive",
        "specifications": {
            "geometry": {
                "type": "primitive",
                "base_shape": "cube",
                "dimensions": {"x": 2.0, "y": 2.0, "z": 2.0}
            }
        },
        "requirements": {"user_request": "Print a 2cm cube"},
        "format_preference": "stl",
        "quality_level": "standard"
    })
    
    print("📋 CAD Agent Result:")
    print(f"Success: {result.success}")
    print(f"Error Message: {result.error_message}")
    print()
    
    print("📊 CAD Data:")
    print(json.dumps(result.data, indent=2))
    
    return result

if __name__ == "__main__":
    asyncio.run(debug_cad_output())
