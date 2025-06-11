#!/usr/bin/env python3

import sys
import os
import asyncio
import json
from pathlib import Path

# Add project root to Python path  
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from agents.research_agent import ResearchAgent

async def debug_research_output():
    """Debug what the research agent outputs for 'Print a 2cm cube'."""
    print("🔍 Debugging Research Agent Output")
    print("=" * 50)
    
    # Initialize research agent
    research_agent = ResearchAgent("debug_research")
    
    # Execute the same task as in the workflow
    result = research_agent.execute_task({
        "task_id": "debug_research",
        "operation": "analyze_and_research", 
        "user_request": "Print a 2cm cube",
        "metadata": {"phase": "research"}
    })
    
    print("📋 Research Agent Result:")
    print(f"Success: {result.success}")
    print(f"Error Message: {result.error_message}")
    print()
    
    print("📊 Research Data:")
    print(json.dumps(result.data, indent=2))
    
    return result

if __name__ == "__main__":
    asyncio.run(debug_research_output())
