Weather Forecast MCP Server (OAuth Enabled)
Overview
This Model Context Protocol (MCP) server is built using FastMCP and FastAPI to provide Large Language Models with real-time weather conditions and forecasts. It implements OAuth 2.0 authorization and authentication compliant with the MCP specification, securing specific endpoints based on user claims.  
TXT
+ 2

Architecture Highlights
FastAPI Integration: The server mounts the standard MCP application into a FastAPI app to expose custom OAuth authorization routes.  
PY

MCP Authorization: It provides the /.well-known/oauth-authorization-server and /authorize endpoints to support OAuth metadata and redirect flows.  
PY

Authentication Validation: The application securely extracts and decodes user claims directly from the x-ms-client-principal header.  
PY

Scope-Based Access Control: Access to sensitive tools is protected by verifying specific scopes, such as api://a0fda4dc-0c43-4c70-8525-9071c619daff/weather.admin.  
PY

Caching Mechanism: Location keys are cached locally in ~/.cache/weather/location_cache.json to optimize performance and reduce redundant API calls.  
PY

Prerequisites & Environment
Ensure you have the required dependencies installed from requirements_2.txt, which includes packages like aiohttp, fastmcp, fastapi, and uvicorn.  
TXT

Configure your .env_2 file with the following required variables:  
Unknown

WEATHER_API_BASE_URL: The weather API base URL (e.g., https://dataservice.accuweather.com).  
Unknown

WEATHER_API_KEY: Your AccuWeather API key.  
Unknown

APP_BASE_URL: The hosted application URL.  
Unknown

TENANT_ID and AZURE_TENANT_ID: Your Azure AD tenant identifiers.  
Unknown

Available MCP Tools
get_current_weather: Retrieves the current weather conditions for a specified location.  
PY

get_5day_forecast: Retrieves the 5-day weather forecast. This tool enforces authorization and requires the user context to have the weather.admin scope.  
PY

get_12hour_forecast: Retrieves the 12-hour hourly weather forecast for a specified location.  
PY

Running the Server
Because the MCP application is mounted on a FastAPI instance to handle the OAuth routes, you should run the server using an ASGI server like uvicorn:

Bash
uvicorn weather:app --host 0.0.0.0 --port 8000
