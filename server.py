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

            query = payload["messages"][-1]["content"]

            response = await model.ainvoke(query)

            data = str(response.content)

            yield encoder.encode(
                TextMessageContentEvent(
                    type=EventType.TEXT_MESSAGE_CONTENT,
                    message_id=message_id,
                    delta=data
                )
            )

            yield encoder.encode(
                TextMessageEndEvent(
                    type=EventType.TEXT_MESSAGE_END,
                    message_id=message_id
                )
            )

            yield encoder.encode(
                ToolCallChunkEvent(
                    type=EventType.TOOL_CALL_CHUNK,
                    tool_call_id="1",
                    tool_call_name="get_weather",
                    parent_message_id=message_id,
                    delta="Weather information:"
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