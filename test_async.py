#!/usr/bin/env python3
"""
Test script for async proxy performance
"""
import asyncio
import aiohttp
import time
import json
from typing import List

PROXY_URL = "http://localhost/proxy"
TEST_REQUESTS = [
    {
        "url": "https://httpbin.org/get",
        "method": "GET"
    },
    {
        "url": "https://httpbin.org/status/200",
        "method": "GET"
    },
    {
        "url": "https://httpbin.org/json",
        "method": "GET"
    },
    {
        "url": "https://api.binance.com/api/v3/ticker/24hr",
        "method": "GET"
    },
    {
        "url": "https://api.bybit.com/v5/market/tickers",
        "method": "GET",
        "params": {"category": "spot"}
    }
]

async def make_proxy_request(session: aiohttp.ClientSession, request_data: dict, request_id: int) -> dict:
    """Make a single proxy request"""
    start_time = time.time()
    
    try:
        async with session.post(PROXY_URL, json=request_data, timeout=aiohttp.ClientTimeout(total=30)) as response:
            try:
                data = await response.json()
                duration = time.time() - start_time
                
                return {
                    "request_id": request_id,
                    "status": response.status,
                    "duration": duration,
                    "success": response.status == 200,
                    "data_length": len(str(data)),
                    "url": request_data.get("url", "unknown")
                }
            except Exception as parse_error:
                # Try to get text response
                text_data = await response.text()
                duration = time.time() - start_time
                
                return {
                    "request_id": request_id,
                    "status": response.status,
                    "duration": duration,
                    "success": response.status == 200,
                    "data_length": len(text_data),
                    "url": request_data.get("url", "unknown"),
                    "parse_error": str(parse_error)
                }
    except asyncio.TimeoutError:
        duration = time.time() - start_time
        return {
            "request_id": request_id,
            "status": "timeout",
            "duration": duration,
            "success": False,
            "error": "Request timeout",
            "url": request_data.get("url", "unknown")
        }
    except Exception as e:
        duration = time.time() - start_time
        return {
            "request_id": request_id,
            "status": "error",
            "duration": duration,
            "success": False,
            "error": str(e),
            "url": request_data.get("url", "unknown")
        }

async def test_concurrent_requests():
    """Test concurrent requests to the proxy"""
    print("🚀 Testing concurrent proxy requests...")
    
    async with aiohttp.ClientSession() as session:
        # Create multiple requests
        tasks = []
        for i in range(5):  # Reduced to 5 concurrent requests for better testing
            for j, test_request in enumerate(TEST_REQUESTS):
                request_id = i * len(TEST_REQUESTS) + j
                task = make_proxy_request(session, test_request, request_id)
                tasks.append(task)
        
        # Execute all requests concurrently
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze results
        successful = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        failed = len(results) - successful
        avg_duration = sum(r.get("duration", 0) for r in results if isinstance(r, dict)) / len(results)
        
        print(f"\n📊 Results:")
        print(f"   Total requests: {len(results)}")
        print(f"   Successful: {successful}")
        print(f"   Failed: {failed}")
        print(f"   Total time: {total_time:.2f}s")
        print(f"   Average duration: {avg_duration:.2f}s")
        print(f"   Requests per second: {len(results)/total_time:.2f}")
        
        # Show detailed results
        print(f"\n📋 Detailed results:")
        for i, result in enumerate(results):
            if isinstance(result, dict):
                status = result.get("status", "unknown")
                duration = result.get("duration", 0)
                url = result.get("url", "unknown")
                error = result.get("error", "")
                print(f"   Request {result.get('request_id')}: {status} ({duration:.2f}s) - {url}")
                if error:
                    print(f"      Error: {error}")
            else:
                print(f"   Request {i}: Exception - {result}")

async def test_single_request():
    """Test a single request to diagnose issues"""
    print("🔍 Testing single request...")
    
    async with aiohttp.ClientSession() as session:
        test_request = {
            "url": "https://httpbin.org/get",
            "method": "GET"
        }
        
        result = await make_proxy_request(session, test_request, 0)
        print(f"   Status: {result.get('status')}")
        print(f"   Duration: {result.get('duration', 0):.2f}s")
        print(f"   Success: {result.get('success')}")
        if result.get("error"):
            print(f"   Error: {result.get('error')}")

async def test_proxy_status():
    """Test proxy status endpoint"""
    print("🔍 Testing proxy status...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("http://localhost/status") as response:
                data = await response.json()
                print(f"   Status: {data.get('status')}")
                print(f"   Requests processed: {data.get('requests_processed')}")
                print(f"   Active requests: {data.get('active_requests')}")
                print(f"   Max concurrent: {data.get('max_concurrent')}")
        except Exception as e:
            print(f"   Error getting status: {e}")

async def main():
    """Main test function"""
    print("🧪 Starting proxy performance tests...")
    
    # Test status first
    await test_proxy_status()
    
    # Test single request
    await test_single_request()
    
    # Test concurrent requests
    await test_concurrent_requests()
    
    # Test status after requests
    print("\n" + "="*50)
    await test_proxy_status()

if __name__ == "__main__":
    asyncio.run(main()) 