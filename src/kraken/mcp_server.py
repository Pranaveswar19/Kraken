import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from kraken.embeddings import generate_embedding
from kraken.vector_store import vector_store
from kraken.config import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

server = Server("kraken")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_timestamp",
            description=(
                "Returns current server timestamp in ISO 8601 format. "
                "Use this to verify MCP connection is working or when user asks for current time."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "include_timezone": {
                        "type": "boolean",
                        "description": "If true, return UTC timezone explicitly. Default: false (local time).",
                        "default": False,
                    }
                },
                "required": [],
            },
        ),
        Tool(
            name="search_messages",
            description=(
                "Search company Slack messages using semantic search. "
                "Returns relevant messages with author, channel, and timestamp. "
                "Use when user asks about past discussions, decisions, or specific topics."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query in natural language (e.g., 'authentication bug', 'database migration')",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 5, max: 20)",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 20,
                    }
                },
                "required": ["query"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    logger.info(f"Tool invoked: {name}, args: {arguments}")
    
    if name == "get_timestamp":
        return await handle_get_timestamp(arguments)
    
    elif name == "search_messages":
        return await handle_search_messages(arguments)
    
    logger.error(f"Unknown tool requested: {name}")
    raise ValueError(f"Unknown tool: {name}")


async def handle_get_timestamp(arguments: dict) -> list[TextContent]:
    include_tz = arguments.get("include_timezone", False)
    
    now = datetime.now(timezone.utc) if include_tz else datetime.now()
    timestamp_str = now.isoformat()
    
    logger.info(f"Returning timestamp: {timestamp_str}")
    
    return [
        TextContent(
            type="text",
            text=f"Current server time: {timestamp_str}",
        )
    ]


async def handle_search_messages(arguments: dict) -> list[TextContent]:
    query = arguments["query"]
    limit = arguments.get("limit", config.DEFAULT_SEARCH_LIMIT)
    
    logger.info(f"Searching for: '{query}', limit: {limit}")
    
    try:
        logger.info("Generating query embedding...")
        embedding, embed_latency, cache_hit = await generate_embedding(query)
        cache_status = "cached" if cache_hit else "generated"
        logger.info(f"Embedding {cache_status} in {embed_latency:.0f}ms")
        
        logger.info("Searching vector store...")
        results = vector_store.search(
            query_embedding=embedding,
            limit=limit,
            min_similarity=config.MIN_SIMILARITY_THRESHOLD
        )
        
        logger.info(f"Found {len(results)} results")
        
        if not results:
            return [
                TextContent(
                    type="text",
                    text=f"No messages found matching '{query}'. Try a different search term or check if data has been synced."
                )
            ]
        
        response_lines = [
            f"Found {len(results)} relevant messages for '{query}':",
            ""
        ]
        
        for i, result in enumerate(results, 1):
            similarity_pct = result["similarity"] * 100
            
            response_lines.extend([
                f"**{i}. {result['author']}** in #{result['channel']} (relevance: {similarity_pct:.0f}%)",
                f"{result['content'][:200]}{'...' if len(result['content']) > 200 else ''}",
                ""
            ])
        
        response_text = "\n".join(response_lines)
        
        logger.info(f"Search complete. Returning {len(results)} results.")
        
        return [
            TextContent(
                type="text",
                text=response_text
            )
        ]
        
    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        
        error_msg = f"Search failed: {str(e)}\n\nPlease try again or contact support if the issue persists."
        
        return [
            TextContent(
                type="text",
                text=error_msg
            )
        ]


async def main() -> None:
    logger.info("Starting Kraken MCP server...")
    logger.info(f"Config: OpenAI model={config.OPENAI_EMBEDDING_MODEL}, cache={'enabled' if config.EMBEDDING_CACHE_ENABLED else 'disabled'}")
    logger.info("Waiting for requests from Claude Desktop on stdin")
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"Server crashed: {e}", exc_info=True)
        raise