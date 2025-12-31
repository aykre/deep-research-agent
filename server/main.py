import asyncio
import json
from datetime import datetime
from typing import Any
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from server.workflow import research_workflow
from server.config import USE_TURNSTILE
from server.services.turnstile import verify_turnstile_token
from server.utils.logging_config import (
    bind_request_context,
    clear_request_context,
    get_logger,
    setup_logging,
)

load_dotenv()

setup_logging()
logger = get_logger(__name__)

app = FastAPI(
    title="Deep Research API",
    description="FastAPI server for deep research",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.websocket("/research")
async def research_websocket(websocket: WebSocket):
    await websocket.accept()
    connection_id = str(uuid4())
    bind_request_context(connection_id=connection_id)

    current_task: asyncio.Task[Any] | None = None
    stop_flag: dict[str, bool] = {"stopped": False}
    writing_flag: dict[str, bool] = {"writing": False}
    is_verified: bool = False  # Track Turnstile verification per WebSocket connection

    async def send_event(event_type: str, data: dict[str, Any]) -> None:
        await websocket.send_json(
            {
                "type": event_type,
                "data": data,
                "timestamp": datetime.now().isoformat(),
            }
        )

    async def run_research(query: str, request_id: str) -> None:
        bind_request_context(request_id=request_id, connection_id=connection_id)
        try:
            inputs = {
                "query": query,
                "stop_flag": stop_flag,
                "request_id": request_id,
                "connection_id": connection_id,
            }

            # Stream with custom mode to receive events from workflow
            async for chunk in research_workflow.astream(inputs, stream_mode="custom"):
                # chunk is the dict we wrote: {"type": "...", "data": {...}}
                event_type = chunk.get("type")
                event_data = chunk.get("data", {})

                if event_type:
                    if event_type == "writing_started":
                        writing_flag["writing"] = True
                    await send_event(event_type, event_data)
        except asyncio.CancelledError:
            # Task was cancelled (likely due to WebSocket disconnect)
            logger.info("Research task cancelled", reason="client_disconnected")
            # Don't attempt to send events - WebSocket is likely closed
            # Re-raise to properly propagate cancellation
            raise
        except Exception as e:
            logger.error("Research workflow failed", error=str(e), exc_info=True)
            await send_event("stopped", {"data": {}})
            await send_event("error", {"message": f"Research workflow error: {str(e)}"})

            # Set stop flag to cancel workflow
            stop_flag["stopped"] = True

    try:
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)
            action = data.get("action")

            if action == "start":
                query = data.get("query")
                request_id = str(uuid4())
                bind_request_context(request_id=request_id, connection_id=connection_id)
                logger.info("Received research query", query=query)

                if not query:
                    await send_event("error", {"message": "Query is required"})
                    continue

                # Verify Turnstile token if enabled and not already verified this session
                if USE_TURNSTILE and not is_verified:
                    turnstile_token = data.get("turnstileToken")
                    if not turnstile_token:
                        await send_event(
                            "error", {"message": "Cloudflare verification required"}
                        )
                        continue

                    logger.info("Verifying turnstile token")
                    is_valid = await verify_turnstile_token(turnstile_token)
                    if not is_valid:
                        logger.info("Invalid turnstile token")
                        await send_event(
                            "error", {"message": "Cloudflare verification failed"}
                        )
                        continue

                    is_verified = True
                    logger.info("WebSocket connection verified via Turnstile")

                # Reset stop flag
                stop_flag["stopped"] = False
                writing_flag["writing"] = False

                # Cancel any existing task
                if current_task and not current_task.done():
                    current_task.cancel()

                logger.info("Starting research task", query=query, task="run_research")
                current_task = asyncio.create_task(
                    run_research(query=query, request_id=request_id)
                )

            elif action == "stop":
                if writing_flag["writing"]:
                    logger.info(
                        "User stopped research during write, rejecting request",
                        writing_in_progress=True,
                    )
                    await send_event(
                        "error",
                        {"message": "Cannot stop research while writing response"},
                    )
                else:
                    logger.info("User stopped research")
                    stop_flag["stopped"] = True
                    await send_event("stopped", {})

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
        stop_flag["stopped"] = True
        if current_task and not current_task.done():
            current_task.cancel()
    except Exception as e:
        logger.error("WebSocket error", error=str(e), exc_info=True)

        # Set stop flag to cancel workflow
        stop_flag["stopped"] = True

        try:
            await send_event("error", {"message": str(e)})
        except Exception:
            pass  # Connection may already be closed
    finally:
        clear_request_context()


def main():
    uvicorn.run("server.main:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
