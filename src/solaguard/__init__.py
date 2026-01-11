"""
SolaGuard MCP Server

Bible-Anchored Theology — Sola Scriptura Enforced

A Protestant Doctrine MCP Server that serves as universal theological infrastructure
for AI applications, providing Scripture-grounded tools with automatic theological
context framing.
"""

__version__ = "0.1.0"
__author__ = "SolaGuard Team"
__email__ = "contact@solaguard.com"
__description__ = "Protestant Doctrine MCP Server - Bible-anchored theological infrastructure for AI applications"

# Lazy imports to avoid initialization issues
def get_app():
    """Get the FastAPI app instance."""
    from .server import app
    return app

def get_main():
    """Get the main function."""
    from .server import main
    return main

__all__ = ["get_app", "get_main", "__version__"]