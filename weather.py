import os

os.environ.pop("SSL_CERT_FILE", None)  # Remove SSL_CERT_FILE from environment variables
os.environ.pop("REQUESTS_CA_BUNDLE", None)  # Remove REQUESTS_CA_BUNDLE from environment variables
os.environ["FASTMCP_DISABLE_VERSION_CHECK"] = "1"  # Disable FastMCP version check

import json
import aiohttp
from pathlib import Path
from typing import Dict, Any, Optional, List
from fastmcp import FastMCP, Context
from dotenv import load_dotenv
import logging
import base64
from fastapi import FastAPI, Request, HTTPException
from starlette.responses import RedirectResponse, JSONResponse
from contextlib import asynccontextmanager
from urllib.parse import urlencode

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WeatherMCPServer")


mcp = FastMCP("Weather-Forecast-Server")
mcp_app = mcp.http_app()

Base_URL = os.environ.get("WEATHER_API_BASE_URL")
API_KEY = os.environ.get("WEATHER_API_KEY")
APP_BASE_URL = os.environ.get("APP_BASE_URL", "https://weather-atcsl-demo.azurewebsites.net")
TENANT_ID = os.environ.get("AZURE_TENANT_ID")

CACHE_DIR = Path.home() / ".cache" / "weather"
LOCATION_CACHE_FILE = CACHE_DIR / "location_cache.json"

app = FastAPI(
    title = "Weather MCP OAuth Server",
    description = "MCP server for fetching weather data with OAuth authentication",
    version = "1.0.0",
    lifespan=mcp_app.lifespan
)

app.mount("/", mcp_app)

@app.get("/.well-known/oauth-authorization-server")
async def oauth_metadata():
    """
    Provides the OAuth 2.0 authorization server metadata.
    """
    metadata = {
        "issuer": f"https://login.microsoftonline.com/{TENANT_ID}/v2.0",
        "authorization_endpoint": f"{APP_BASE_URL}/authorize",
        "token_endpoint": f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token",
        "response_types_supported": ["code"],
        "jwks_uri": f"https://login.microsoftonline.com/{TENANT_ID}/discovery/v2.0/keys",
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "scopes_supported": ["api://a0fda4dc-0c43-4c70-8525-9071c619daff/weather.admin"],
        "code_challenge_methods_supported": ["S256"]
        
    }
    return JSONResponse(content=metadata)

@app.get("/authorize")
async def authorize_proxy(request: Request):
    params = dict(request.query_params)
    params["prompt"] = "login consent"
    existing_scopes = params.get("scope", "")

    additional_scopes = (
        " api://5cfa2a1e-5c73-4c92-ab40-207d0230d083/weather.admin"
    )

    params["scope"] = (
        existing_scopes + " " + "".join(additional_scopes)
    ).strip()

    auth_url = (f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/authorize")
    query_string = urlencode(params) #(request.query_params.multi_items())
    redirect_url = f"{auth_url}?{query_string}"
    return RedirectResponse(url=redirect_url)

def extract_claims(ctx: Context):
    encoded_principal = (ctx.request_context.request.headers.get("x-ms-client-principal"))
    authorization = ctx.request_context.request.headers.get("authorization")
    
    if not encoded_principal:
        raise HTTPException(status_code=401, detail="Authentication required: Missing x-ms-client-principal header")
    
    try:
        decoded_json = base64.b64decode(encoded_principal).decode("utf-8")
        principal = json.loads(decoded_json)
        return principal.get("claims", [])
    
    except Exception as e:
        logger.error(f"Error decoding claims: {e}")
        raise HTTPException(status_code=403, detail="Invalid authenticationm claims")

def authorize_scope(required_scope: str, ctx: Context):
    claims = extract_claims(ctx)
    scopes = [claim["val"] for claim in claims if claim["typ"] == "scp"]

    
    if required_scope not in scopes:
        raise HTTPException(status_code=403, detail="Insufficient permissions: Required scope not found")

#------Cache Management Helpers------#
def get_cached_location_key(location:str) -> Optional[str]:
    """
    Retrieves the location key from the cache if it exists.
    """
    if not LOCATION_CACHE_FILE.exists():
        return None
    
    try:
        with open(LOCATION_CACHE_FILE, "r") as f:
            cache = json.load(f)
        return cache.get(location)
    except Exception as e:
        logging.error(f"Error reading location cache: {e}")
        return None
    
def cache_location_key(location:str, location_key:str) -> None:
    """
    Caches the location key for a given location.
    """
    try:
        if not LOCATION_CACHE_FILE.exists():
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache = {}
        else:
            with open(LOCATION_CACHE_FILE, "r") as f:
                cache = json.load(f)
        
        cache[location] = location_key
        
        with open(LOCATION_CACHE_FILE, "w") as f:
            json.dump(cache, f, indent = 4)
    except Exception as e:
        logging.error(f"Error writing to location cache: {e}")

#-----------------------------------------#

async def resolve_location_key(location:str, session:aiohttp.ClientSession) -> str:
    """
    Checks the cache for a location key. If not found, queries the API and updates the cache.
    """
    cached_key = get_cached_location_key(location) #function needs to be created to retrieve the location key from the cache
    if cached_key:
        logging.info(f"Location key for '{location}' found in cache.")
        return cached_key
    
    api_key = os.environ.get("WEATHER_API_KEY")
    search_url = f"{Base_URL}/locations/v1/cities/search"
    headers = {"Authorization": f"Bearer {api_key}"}
    params = {"q": location}
    async with session.get(search_url, headers=headers, params=params) as response:
        if response.status != 200:
            logging.error(f"Failed to fetch location key for '{location}': {response.status}")
            error_text = await response.text()
            raise Exception(f"Failed to fetch location key for '{location}': {response.status} - {error_text}")
        
        data = await response.json()
        if not data or not isinstance(data, list):
            raise Exception(f"No valid location data found for '{location}'")

        location_key = data[0]["Key"]
        
        cache_location_key(location, location_key) #function needs to be created to cache the location key
        return location_key

#-------Get Current Weather Conditions-------#
@mcp.tool
async def get_current_weather(Location: str, details: bool = False) ->List[Dict[str, Any]]:
    """Fetches the current weather conditions for a specified location."""
    api_key = API_KEY
    headers = {
        "Authorization": f"Bearer {api_key}"
    }

    async with aiohttp.ClientSession() as session:
        location_key = await resolve_location_key(Location, session)
        weather_url = f"{Base_URL}/currentconditions/v1/{location_key}"
        params = {"details": str(details).lower()}
        

        async with session.get(weather_url, headers=headers, params=params) as response:
            if response.status != 200:
                logging.error(f"Failed to fetch weather data for '{Location}': {response.status}")
                error_text = await response.text()
                raise Exception(f"Failed to fetch weather data for '{Location}': {response.status} - {error_text}")
            
            weather_data = await response.json()
            return weather_data
        

#-----------get 5-day weather forecast-----------#
@mcp.tool
async def get_5day_forecast(Location: str, metric: bool = False, ctx: Context = None) -> Dict[str, Any]:
    """Fetches the 5-day weather forecast for a specified location."""

    authorize_scope("api://a0fda4dc-0c43-4c70-8525-9071c619daff/weather.admin", ctx)
    api_key = API_KEY
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    async with aiohttp.ClientSession() as session:
        location_key = await resolve_location_key(Location, session)
        forecast_url = f"{Base_URL}/forecasts/v1/daily/5day/{location_key}"
        params = {"details": str(metric).lower()}
        
        async with session.get(forecast_url, headers=headers, params=params) as response:
            if response.status != 200:
                logging.error(f"Failed to fetch forecast data for '{Location}': {response.status}")
                error_text = await response.text()
                raise Exception(f"Failed to fetch forecast data for '{Location}': {response.status} - {error_text}")
            
            forecast_data = await response.json()
            return forecast_data
        

#------------get 12-hour weather forecast-----------#
@mcp.tool
async def get_12hour_forecast(Location: str, metric: bool = False) -> List[Dict[str, Any]]:
    """Fetches the 12-hour weather forecast for a specified location."""
    api_key = API_KEY
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    async with aiohttp.ClientSession() as session:
        location_key = await resolve_location_key(Location, session)
        forecast_url = f"{Base_URL}/forecasts/v1/hourly/12hour/{location_key}"
        params = {"details": str(metric).lower()}
        
        async with session.get(forecast_url, headers=headers, params=params) as response:
            if response.status != 200:
                logging.error(f"Failed to fetch hourly forecast data for '{Location}': {response.status}")
                error_text = await response.text()
                raise Exception(f"Failed to fetch hourly forecast data for '{Location}': {response.status} - {error_text}")
            
            hourly_forecast_data = await response.json()
            return hourly_forecast_data
