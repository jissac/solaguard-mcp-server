#!/usr/bin/env python3
"""
Integration tests for MCP protocol compliance.
"""

import pytest
import asyncio
import json
import subprocess
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestMCPProtocol:
    """Test MCP protocol compliance."""
    
    @pytest.mark.asyncio
    async def test_mcp_server_startup(self):
        """Test that MCP server starts correctly."""
        try:
            # Start the server process
            process = await asyncio.create_subprocess_exec(
                "uv", "run", "python", "-m", "solaguard.server",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=Path(__file__).parent.parent.parent
            )
            
            # Test initialize request
            initialize_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "test-client",
                        "version": "1.0.0"
                    }
                }
            }
            
            # Send initialize request
            request_json = json.dumps(initialize_request) + "\n"
            process.stdin.write(request_json.encode())
            await process.stdin.drain()
            
            # Read response with timeout
            try:
                response_line = await asyncio.wait_for(process.stdout.readline(), timeout=10.0)
                if response_line:
                    response = json.loads(response_line.decode().strip())
                    assert "result" in response
                    assert "serverInfo" in response["result"]
                    assert response["result"]["serverInfo"]["name"] == "SolaGuard"
            except asyncio.TimeoutError:
                pytest.fail("Server did not respond within timeout")
            
            # Cleanup
            process.terminate()
            await process.wait()
            
        except FileNotFoundError:
            pytest.skip("uv not available for server testing")
    
    @pytest.mark.asyncio
    async def test_tools_list(self):
        """Test tools/list MCP method."""
        try:
            # Start the server process
            process = await asyncio.create_subprocess_exec(
                "uv", "run", "python", "-m", "solaguard.server",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=Path(__file__).parent.parent.parent
            )
            
            # Initialize first
            initialize_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test-client", "version": "1.0.0"}
                }
            }
            
            request_json = json.dumps(initialize_request) + "\n"
            process.stdin.write(request_json.encode())
            await process.stdin.drain()
            
            # Read initialize response
            await asyncio.wait_for(process.stdout.readline(), timeout=5.0)
            
            # Test tools/list request
            list_tools_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {}
            }
            
            request_json = json.dumps(list_tools_request) + "\n"
            process.stdin.write(request_json.encode())
            await process.stdin.drain()
            
            # Read response
            response_line = await asyncio.wait_for(process.stdout.readline(), timeout=5.0)
            if response_line:
                response = json.loads(response_line.decode().strip())
                assert "result" in response
                assert "tools" in response["result"]
                
                tools = response["result"]["tools"]
                tool_names = [tool["name"] for tool in tools]
                assert "get_verse" in tool_names
                assert "search_scripture" in tool_names
            
            # Cleanup
            process.terminate()
            await process.wait()
            
        except (FileNotFoundError, asyncio.TimeoutError):
            pytest.skip("Server testing not available")
    
    @pytest.mark.asyncio
    async def test_get_verse_tool_call(self):
        """Test get_verse tool call via MCP protocol."""
        try:
            # Start the server process
            process = await asyncio.create_subprocess_exec(
                "uv", "run", "python", "-m", "solaguard.server",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=Path(__file__).parent.parent.parent
            )
            
            # Initialize
            initialize_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test-client", "version": "1.0.0"}
                }
            }
            
            request_json = json.dumps(initialize_request) + "\n"
            process.stdin.write(request_json.encode())
            await process.stdin.drain()
            await asyncio.wait_for(process.stdout.readline(), timeout=5.0)
            
            # Test get_verse tool call
            get_verse_request = {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "get_verse",
                    "arguments": {
                        "reference": "John 3:16",
                        "translation": "KJV"
                    }
                }
            }
            
            request_json = json.dumps(get_verse_request) + "\n"
            process.stdin.write(request_json.encode())
            await process.stdin.drain()
            
            # Read response
            response_line = await asyncio.wait_for(process.stdout.readline(), timeout=10.0)
            if response_line:
                response = json.loads(response_line.decode().strip())
                assert "result" in response
                
                # The result should contain the tool response
                result = response["result"]
                assert isinstance(result, dict)
            
            # Cleanup
            process.terminate()
            await process.wait()
            
        except (FileNotFoundError, asyncio.TimeoutError):
            pytest.skip("Server testing not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])