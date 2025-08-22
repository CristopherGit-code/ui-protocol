# AG-UI-DEMO

> [!NOTE]  
> Last update 8-22-2025

Implementation of AG-UI server streaming events to front to generate UI components

## Features

- [server.py](server.py) Main server file that includes the streaming logic, integrates langgraph + OCI agent with a simple weather tool call.

This file has a tool created to retrieve real time weather information. The *react agent* is build using OCI openAI client. The streaming ```POST``` method is streaming an event for each step of the agent call, this events are converted to visual UI components.

- [ag-ui-test](ag-ui-test) This is the lite react application enhanced by *Vite* for reaching the python server.

- [Main page](ag-ui-test/src/App.jsx) The main App page has a complex react implementation, the logic gets the messages from the user, makes a ```POST``` request to the server, and since this funciton is an ```async```, it uses a reader to catch all the events streamed from the back.

```handleEvent``` function classificates the events and generates some UI components depending on the event information from the server.

-[util](util) Folder containing the setup of the OCI agent with credentials

## Setup

1. Get the necessary dependencies (use python venv / toml)
2. ```cd ag-ui-test``` and do ```npm install``` for the basic react integration
3. Create .evn file to setup the OCI keys from sandbox
    - Ensure to modify the [yaml file](util/config/config.yaml) to add the necessary variables
4. Run the python server using ```uv run server.py```
5. Run the react app using ```npm run dev```
6. Send messages from the client and wait for event responses.

## Basic walkthrough

