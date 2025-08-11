from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
import httpx
import asyncio
import time
import json
import os
from typing import Dict, Any, Optional
from pydantic import BaseModel
from dotenv import load_dotenv
import multiprocessing

load_dotenv()

app = FastAPI(
    title="Crypto Exchange VPN Proxy",
    description="Unified VPN Proxy server for bypassing IP restrictions on crypto exchanges",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration optimized for t2.micro
PROXY_TIMEOUT = 30.0
MAX_RETRIES = 3
RATE_LIMIT_DELAY = 0.05  # 50ms between requests (faster for t2.micro)
MAX_CONCURRENT_REQUESTS = 10  # Limit concurrent requests for t2.micro
WORKERS_PER_CORE = 1  # Conservative for t2.micro

# Request tracking
request_count = 0
last_request_time = 0
active_requests = 0

class ProxyRequest(BaseModel):
    url: str
    method: str = "GET"
    params: Optional[Dict[str, Any]] = None
    headers: Optional[Dict[str, str]] = None
    data: Optional[Any] = None
    json_data: Optional[Dict[str, Any]] = None

class ExchangeProxy:
    def __init__(self):
        # Optimize client for t2.micro
        self.client = httpx.AsyncClient(
            timeout=PROXY_TIMEOUT,
            follow_redirects=True,
            limits=httpx.Limits(
                max_connections=20,  # Conservative for t2.micro
                max_keepalive_connections=10,
                keepalive_expiry=30.0
            ),
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Encoding": "gzip, deflate, br"  # Accept compressed responses
            }
        )
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    
    async def make_request(self, proxy_request: ProxyRequest) -> Dict[str, Any]:
        """Make HTTP request with rate limiting and retry logic"""
        global request_count, last_request_time, active_requests
        
        async with self.semaphore:  # Limit concurrent requests
            active_requests += 1
            
            try:
                # Rate limiting
                current_time = time.time()
                if current_time - last_request_time < RATE_LIMIT_DELAY:
                    await asyncio.sleep(RATE_LIMIT_DELAY)
                last_request_time = time.time()
                
                request_count += 1
                
                # Prepare headers
                request_headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",  # Accept compressed responses
                    "Connection": "keep-alive",
                }
                
                if proxy_request.headers:
                    request_headers.update(proxy_request.headers)
                
                # Prepare data
                request_data = None
                if proxy_request.json_data:
                    request_data = proxy_request.json_data
                elif proxy_request.data:
                    request_data = proxy_request.data
                
                # Retry logic
                for attempt in range(MAX_RETRIES):
                    try:
                        method = proxy_request.method.upper()
                        
                        if method == "GET":
                            response = await self.client.get(
                                proxy_request.url, 
                                headers=request_headers, 
                                params=proxy_request.params
                            )
                        elif method == "POST":
                            response = await self.client.post(
                                proxy_request.url, 
                                headers=request_headers, 
                                params=proxy_request.params,
                                json=request_data if isinstance(request_data, dict) else None,
                                data=request_data if not isinstance(request_data, dict) else None
                            )
                        elif method == "PUT":
                            response = await self.client.put(
                                proxy_request.url, 
                                headers=request_headers, 
                                params=proxy_request.params,
                                json=request_data if isinstance(request_data, dict) else None,
                                data=request_data if not isinstance(request_data, dict) else None
                            )
                        elif method == "DELETE":
                            response = await self.client.delete(
                                proxy_request.url, 
                                headers=request_headers, 
                                params=proxy_request.params
                            )
                        else:
                            raise HTTPException(status_code=400, detail=f"Unsupported method: {method}")
                        
                        response.raise_for_status()
                        
                        # Try to parse as JSON, fallback to text
                        try:
                            # Get the raw text first to handle encoding issues
                            response_text = response.text
                            response_data = response.json() if response_text.strip() else {}
                            
                            return {
                                "status_code": response.status_code,
                                "headers": dict(response.headers),
                                "data": response_data,
                                "success": True,
                                "method": method,
                                "url": proxy_request.url
                            }
                        except Exception as parse_error:
                            # If JSON parsing fails, return text
                            return {
                                "status_code": response.status_code,
                                "headers": dict(response.headers),
                                "data": response.text,
                                "success": True,
                                "method": method,
                                "url": proxy_request.url,
                                "parse_warning": f"JSON parse failed: {str(parse_error)}"
                            }
                            
                    except httpx.HTTPStatusError as e:
                        if attempt == MAX_RETRIES - 1:
                            return {
                                "status_code": e.response.status_code,
                                "headers": dict(e.response.headers),
                                "data": e.response.text,
                                "success": False,
                                "error": f"HTTP {e.response.status_code}: {e.response.text}",
                                "method": method,
                                "url": proxy_request.url
                            }
                        await asyncio.sleep(1 * (2 ** attempt))  # Exponential backoff
                        
                    except Exception as e:
                        if attempt == MAX_RETRIES - 1:
                            return {
                                "status_code": 500,
                                "data": None,
                                "success": False,
                                "error": str(e),
                                "method": method,
                                "url": proxy_request.url
                            }
                        await asyncio.sleep(1 * (2 ** attempt))
            finally:
                active_requests -= 1

proxy = ExchangeProxy()

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Crypto Exchange VPN Proxy",
        "version": "1.0.0",
        "requests_processed": request_count,
        "active_requests": active_requests,
        "max_concurrent": MAX_CONCURRENT_REQUESTS
    }

@app.post("/proxy")
async def unified_proxy(proxy_request: ProxyRequest):
    """Unified proxy endpoint for all HTTP requests"""
    print(f"🔄 Proxying {proxy_request.method} request to: {proxy_request.url}")
    print(f"📋 Parameters: {proxy_request.params}")
    print(f"📦 Data: {proxy_request.data or proxy_request.json_data}")
    print(f"🔧 Headers: {proxy_request.headers}")
    print(f"👥 Active requests: {active_requests}/{MAX_CONCURRENT_REQUESTS}")
    
    result = await proxy.make_request(proxy_request)
    
    if result["success"]:
        # Create response without Content-Length to avoid issues with large responses
        response_headers = dict(result["headers"])
        
        # Remove problematic headers
        response_headers.pop("content-length", None)
        response_headers.pop("Content-Length", None)
        response_headers.pop("transfer-encoding", None)
        response_headers.pop("Transfer-Encoding", None)
        response_headers.pop("content-encoding", None)
        response_headers.pop("Content-Encoding", None)
        
        # Add our own headers
        response_headers["X-Proxy-Status"] = "success"
        response_headers["X-Proxy-Method"] = result["method"]
        response_headers["X-Proxy-URL"] = result["url"]
        response_headers["X-Proxy-Active-Requests"] = str(active_requests)
        
        # Determine content type
        content_type = "application/json"
        if isinstance(result["data"], str):
            content_type = "text/plain"
        
        return Response(
            content=json.dumps(result["data"]) if isinstance(result["data"], (dict, list)) else str(result["data"]),
            status_code=result["status_code"],
            headers=response_headers,
            media_type=content_type
        )
    else:
        raise HTTPException(
            status_code=result["status_code"],
            detail=result["error"]
        )

@app.get("/status")
async def get_status():
    """Get proxy server status and statistics"""
    return {
        "status": "running",
        "requests_processed": request_count,
        "active_requests": active_requests,
        "max_concurrent": MAX_CONCURRENT_REQUESTS,
        "uptime": time.time(),
        "rate_limit_delay": RATE_LIMIT_DELAY,
        "max_retries": MAX_RETRIES,
        "timeout": PROXY_TIMEOUT,
        "workers_per_core": WORKERS_PER_CORE
    }

if __name__ == "__main__":
    import uvicorn
    
    cpu_count = multiprocessing.cpu_count()
    workers = max(1, min(cpu_count * WORKERS_PER_CORE, 2)) 
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        workers=workers,
        log_level="info",
        access_log=True
    ) 