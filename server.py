import os
import uvicorn
import uuid
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from ag_ui.core import (
    RunAgentInput,
    EventType,
    RunStartedEvent,
    RunFinishedEvent,
    TextMessageStartEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    ToolCallChunkEvent,
    RunErrorEvent
)
from ag_ui.encoder import EventEncoder
from fastapi.middleware.cors import CORSMiddleware
from util.openai_client import LLM_Open_Client
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
from langchain_core.messages import AIMessage, ToolMessage
import httpx
from typing import Any

app = FastAPI(title="AG-UI Endpoint")

# Test purposes open
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oci_client = LLM_Open_Client()
model = oci_client.build_llm_client()

NWS_API_BASE = "https://api.weather.gov"
USER_AGENT = "weather-app/1.0"

async def make_nws_request(url: str) -> dict[str, Any] | None:
    """Make a request to the NWS API with proper error handling."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/geo+json"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None

@tool
async def get_forecast(latitude: float, longitude: float) -> str:
    """Get weather forecast for a location.

    Args:
        latitude: Latitude of the location
        longitude: Longitude of the location
    """
    # First get the forecast grid endpoint
    points_url = f"{NWS_API_BASE}/points/{latitude},{longitude}"
    points_data = await make_nws_request(points_url)

    if not points_data:
        return "Unable to fetch forecast data for this location."

    # Get the forecast URL from the points response
    forecast_url = points_data["properties"]["forecast"]
    forecast_data = await make_nws_request(forecast_url)

    if not forecast_data:
        return "Unable to fetch detailed forecast."

    # Format the periods into a readable forecast
    periods = forecast_data["properties"]["periods"]
    return periods[0]

agent = create_react_agent(
    model=model,
    tools=[get_forecast]
)

@app.post("/")
async def agentic_chat_endpoint(input_data: RunAgentInput, request: Request):
    """Agentic chat endpoint"""
    # Get the accept header from the request
    accept_header = request.headers.get("accept")

    # Create an event encoder to properly format SSE events
    encoder = EventEncoder(accept=accept_header)

    async def event_generator():
        try:

            # Send run started event
            yield encoder.encode(
            RunStartedEvent(
                type=EventType.RUN_STARTED,
                thread_id=input_data.thread_id,
                run_id=input_data.run_id
            ),
            )

            message_id = str(uuid.uuid4())

            yield encoder.encode(
                TextMessageStartEvent(
                    type=EventType.TEXT_MESSAGE_START,
                    message_id=message_id,
                    role="assistant",
                )
            )

            messages = [
                {"role": message.role, "content": message.content} for message in input_data.messages
            ]

            payload = {"messages":messages}
            
            try:
                async for chunk in agent.astream(payload,stream_mode="values"):
                    message = chunk['messages'][-1]
                    # print("MESSAGE =================")
                    # print(message)
                    if isinstance(message,AIMessage) and message.content:
                        # print("++++++++++ Entered AI MESSAGE")
                        yield encoder.encode(
                            TextMessageContentEvent(
                                type=EventType.TEXT_MESSAGE_CONTENT,
                                message_id=message_id,
                                delta=message.content
                            )
                        )
                    elif isinstance(message,ToolMessage):
                        # print("============= Entered TOOL MESSAGE")
                        # print(message)
                        yield encoder.encode(
                            ToolCallChunkEvent(
                                type=EventType.TOOL_CALL_CHUNK,
                                tool_call_id=message.tool_call_id,
                                tool_call_name=message.name,
                                parent_message_id=message_id,
                                delta=message.content
                            )
                        )
                    else:
                        pass
            except Exception as e:
                yield encoder.encode(
                    TextMessageContentEvent(
                        type=EventType.TEXT_MESSAGE_CONTENT,
                        message_id=message_id,
                        delta=f"Error in response: {e}"
                    )
                )

            yield encoder.encode(
                TextMessageEndEvent(
                    type=EventType.TEXT_MESSAGE_END,
                    message_id=message_id
                )
            )

            # Send run finished event
            yield encoder.encode(
            RunFinishedEvent(
                type=EventType.RUN_FINISHED,
                thread_id=input_data.thread_id,
                run_id=input_data.run_id
            ),
            )
        except Exception as e:
            yield encoder.encode(
                RunErrorEvent(
                    type=EventType.RUN_ERROR,
                    message=str(e)
                )
            )

    return StreamingResponse(
        event_generator(),
        media_type=encoder.get_content_type()
    )

def main():
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )

if __name__ == "__main__":
    main()