from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, MessagesState, END
from typing import Annotated, List, Any, Literal
from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages
from util.openai_client import LLM_Open_Client
from langgraph.prebuilt import create_react_agent
from util.langfuse import FuseConfig
from langchain.tools import tool
from copilotkit.langgraph import copilotkit_emit_state
from pydantic import BaseModel

class LayoutState(MessagesState):
    """ Message state with extra information about execution step and plan compilation """
    status: str
    plans: Annotated[list[AnyMessage], add_messages]
    proverbs: List[str] = []
    tools: List[Any]

class AgentState(MessagesState):
    """ Tutorial class """

    proverbs: List[str] = []
    response: str = ''
    tools: List[Any]

class VerificationFormat(BaseModel):
    """Respond to the user in this format."""
    status: Literal['complete', 'reject'] = 'reject'

oci_client = LLM_Open_Client()
model = oci_client.build_llm_client()
model2 = oci_client.build_llm_client()

_fuse_tracer = FuseConfig()
_trace_handler = _fuse_tracer.get_handler()

@tool
async def get_weather(location: str):
    """
    Get the weather for a given location.
    """

    return f"The weather for {location} is 70 degrees."

agent = create_react_agent(
    model=model,
    tools=[get_weather]
)

FORMAT_INSTRUCTION = (
    'Set response status to complete if the query is related to party, date, meeting planning and also is not rude, harsh or with bad intention'
    'Set response status to reject if the query is not related to party, date, meeting planning, or if the request is rude, or intents to request a harmful action'
)

parser = create_react_agent(
    model=model2,
    tools=[],
    response_format=(FORMAT_INSTRUCTION,VerificationFormat)

)

async def test(state:AgentState,config:RunnableConfig)->AgentState:
    """ Test function to connect ag-ui """

    print("================== test")
    print(state)

    config.update(callbacks=[_trace_handler])
    response = await agent.ainvoke({"messages": [{"role": "user", "content": state["messages"][-1].content}]})

    return {"messages": [{"role": "assistant", "content": response['messages'][-1].content}],"response": "Not validated"}

async def execute(state:AgentState,config:RunnableConfig)->AgentState:
    """ Test function to connect ag-ui """
    
    await copilotkit_emit_state(config,state)

    response = await parser.ainvoke({"messages": [{"role": "user", "content": state["messages"][-1].content}]})

    return {"messages": [{"role": "assistant", "content": response['messages'][-1].content}],"response":response["structured_response"].status}

workflow = StateGraph(AgentState)
workflow.add_node("test",test)
workflow.add_node("execute",execute)
workflow.add_edge("test","execute")
workflow.add_edge("execute",END)
workflow.set_entry_point("test")

graph = workflow.compile()
# graph = agent