# Weather Forecast MCP Server (OAuth Enabled)

## Overview

This Model Context Protocol (MCP) server is built using `FastMCP` and `FastAPI` to provide Large Language Models with real-time weather conditions and forecasts. It implements OAuth 2.0 authorization and authentication compliant with the MCP specification, securing specific endpoints based on user claims.

## Architecture Highlights

*   **FastAPI Integration:** The server mounts the standard MCP application into a `FastAPI` app to expose custom OAuth authorization routes.
*   **MCP Authorization:** It provides the `/.well-known/oauth-authorization-server` and `/authorize` endpoints to support OAuth metadata and redirect flows.
*   **Authentication Validation:** The application securely extracts and decodes user claims directly from the `x-ms-client-principal` header.
*   **Scope-Based Access Control:** Access to sensitive tools is protected by verifying specific scopes, such as `api://a0fda4dc-0c43-4c70-8525-9071c619daff/weather.admin`.
*   **Caching Mechanism:** Location keys are cached locally in `~/.cache/weather/location_cache.json` to optimize performance and reduce redundant API calls.

## Prerequisites & Environment

Ensure you have the required dependencies installed from `requirements.txt`, which includes packages like `aiohttp`, `fastmcp`, `fastapi`, and `uvicorn`. 

Configure your `.env` file with the following required variables:

```env
WEATHER_API_BASE_URL=https://dataservice.accuweather.com
WEATHER_API_KEY=your_accuweather_api_key
APP_BASE_URL=https://your-app-service.azurewebsites.net
TENANT_ID=your_azure_tenant_id
AZURE_TENANT_ID=your_azure_tenant_id
```

## Available MCP Tools

### 1. `get_current_weather`
*   **Description**: Retrieves the current weather conditions for a specified location.

### 2. `get_5day_forecast`
*   **Description**: Retrieves the 5-day weather forecast. This tool enforces authorization and requires the user context to have the `weather.admin` scope.

### 3. `get_12hour_forecast`
*   **Description**: Retrieves the 12-hour hourly weather forecast for a specified location.

## Running the Server

Because the MCP application is mounted on a FastAPI instance to handle the OAuth routes, you should run the server using an ASGI server like `uvicorn`:

```bash
uvicorn weather_2:app --host 0.0.0.0 --port 8000
```
