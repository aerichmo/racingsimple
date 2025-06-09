#!/usr/bin/env python3
"""
Debug script for diagnosing upload issues to https://stall10n.onrender.com/
"""

import os
import sys
import time
import json
import mimetypes
import requests
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime

class UploadDebugger:
    def __init__(self, server_url="https://stall10n.onrender.com/"):
        self.server_url = server_url.rstrip('/')
        self.session = requests.Session()
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "server_url": self.server_url,
            "tests": {}
        }
    
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
    
    def test_connectivity(self):
        """Test basic connectivity to the server"""
        self.log("Testing server connectivity...")
        test_name = "connectivity"
        
        try:
            response = self.session.get(self.server_url, timeout=10)
            self.results["tests"][test_name] = {
                "status": "PASS",
                "status_code": response.status_code,
                "response_time": response.elapsed.total_seconds(),
                "headers": dict(response.headers)
            }
            self.log(f"✓ Server reachable - Status: {response.status_code} - Response time: {response.elapsed.total_seconds():.2f}s")
            return True
        except requests.exceptions.Timeout:
            self.results["tests"][test_name] = {"status": "FAIL", "error": "Connection timeout"}
            self.log("✗ Connection timeout", "ERROR")
            return False
        except requests.exceptions.ConnectionError as e:
            self.results["tests"][test_name] = {"status": "FAIL", "error": str(e)}
            self.log(f"✗ Connection error: {e}", "ERROR")
            return False
        except Exception as e:
            self.results["tests"][test_name] = {"status": "FAIL", "error": str(e)}
            self.log(f"✗ Unexpected error: {e}", "ERROR")
            return False
    
    def test_ssl_certificate(self):
        """Test SSL certificate validity"""
        self.log("Testing SSL certificate...")
        test_name = "ssl_certificate"
        
        try:
            response = self.session.get(self.server_url, verify=True)
            self.results["tests"][test_name] = {"status": "PASS", "verified": True}
            self.log("✓ SSL certificate is valid")
            return True
        except requests.exceptions.SSLError as e:
            self.results["tests"][test_name] = {"status": "FAIL", "error": str(e)}
            self.log(f"✗ SSL certificate error: {e}", "ERROR")
            return False
    
    def check_file(self, file_path):
        """Validate the file before upload"""
        self.log(f"Checking file: {file_path}")
        test_name = "file_validation"
        
        path = Path(file_path)
        results = {
            "exists": path.exists(),
            "is_file": path.is_file() if path.exists() else False,
            "readable": os.access(file_path, os.R_OK) if path.exists() else False,
            "size": path.stat().st_size if path.exists() else 0,
            "mime_type": mimetypes.guess_type(file_path)[0] if path.exists() else None
        }
        
        if not results["exists"]:
            self.log(f"✗ File does not exist: {file_path}", "ERROR")
            self.results["tests"][test_name] = {"status": "FAIL", "error": "File not found", "details": results}
            return False
        
        if not results["is_file"]:
            self.log(f"✗ Path is not a file: {file_path}", "ERROR")
            self.results["tests"][test_name] = {"status": "FAIL", "error": "Not a file", "details": results}
            return False
        
        if not results["readable"]:
            self.log(f"✗ File is not readable: {file_path}", "ERROR")
            self.results["tests"][test_name] = {"status": "FAIL", "error": "Permission denied", "details": results}
            return False
        
        self.log(f"✓ File exists and is readable")
        self.log(f"  - Size: {results['size']:,} bytes ({results['size'] / 1024 / 1024:.2f} MB)")
        self.log(f"  - MIME type: {results['mime_type'] or 'Unknown'}")
        
        self.results["tests"][test_name] = {"status": "PASS", "details": results}
        return True
    
    def test_upload_endpoints(self):
        """Test common upload endpoints"""
        self.log("Testing upload endpoints...")
        test_name = "upload_endpoints"
        
        endpoints = [
            "/upload",
            "/api/upload", 
            "/file/upload",
            "/files",
            "/"
        ]
        
        results = {}
        for endpoint in endpoints:
            url = f"{self.server_url}{endpoint}"
            try:
                # Test OPTIONS request first
                options_response = self.session.options(url, timeout=5)
                
                # Test POST with empty data
                post_response = self.session.post(url, timeout=5)
                
                results[endpoint] = {
                    "options_status": options_response.status_code,
                    "post_status": post_response.status_code,
                    "allows_post": "POST" in options_response.headers.get("Allow", ""),
                    "cors_headers": {
                        "Access-Control-Allow-Origin": options_response.headers.get("Access-Control-Allow-Origin"),
                        "Access-Control-Allow-Methods": options_response.headers.get("Access-Control-Allow-Methods")
                    }
                }
                
                if post_response.status_code in [200, 400, 405, 422]:
                    self.log(f"✓ Endpoint {endpoint} responds: {post_response.status_code}")
                
            except Exception as e:
                results[endpoint] = {"error": str(e)}
        
        self.results["tests"][test_name] = results
        return True
    
    def attempt_upload(self, file_path, endpoint="/upload"):
        """Attempt to upload the file with detailed logging"""
        self.log(f"Attempting file upload to {endpoint}...")
        test_name = "upload_attempt"
        
        url = f"{self.server_url}{endpoint}"
        
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (os.path.basename(file_path), f, mimetypes.guess_type(file_path)[0] or 'application/octet-stream')}
                
                # Log request details
                self.log(f"  - URL: {url}")
                self.log(f"  - Method: POST")
                self.log(f"  - File field name: 'file'")
                
                # Make request with detailed error handling
                response = self.session.post(
                    url,
                    files=files,
                    timeout=60,
                    allow_redirects=True
                )
                
                # Log response details
                self.log(f"  - Response status: {response.status_code}")
                self.log(f"  - Response headers: {dict(response.headers)}")
                
                # Try to parse response body
                try:
                    response_data = response.json()
                    self.log(f"  - Response JSON: {json.dumps(response_data, indent=2)}")
                except:
                    self.log(f"  - Response text: {response.text[:500]}...")
                
                self.results["tests"][test_name] = {
                    "status": "PASS" if response.status_code == 200 else "FAIL",
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "body": response.text[:1000],
                    "url": response.url,
                    "history": [r.status_code for r in response.history]
                }
                
                if response.status_code == 200:
                    self.log("✓ Upload successful!")
                else:
                    self.log(f"✗ Upload failed with status {response.status_code}", "ERROR")
                
                return response.status_code == 200
                
        except requests.exceptions.Timeout:
            self.results["tests"][test_name] = {"status": "FAIL", "error": "Upload timeout"}
            self.log("✗ Upload timeout (60s exceeded)", "ERROR")
            return False
        except Exception as e:
            self.results["tests"][test_name] = {"status": "FAIL", "error": str(e)}
            self.log(f"✗ Upload error: {e}", "ERROR")
            return False
    
    def test_server_health(self):
        """Test common health check endpoints"""
        self.log("Testing server health endpoints...")
        test_name = "health_check"
        
        health_endpoints = [
            "/health",
            "/api/health",
            "/status",
            "/_health",
            "/ping"
        ]
        
        results = {}
        for endpoint in health_endpoints:
            url = f"{self.server_url}{endpoint}"
            try:
                response = self.session.get(url, timeout=5)
                results[endpoint] = {
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds(),
                    "body": response.text[:200]
                }
                
                if response.status_code == 200:
                    self.log(f"✓ Health endpoint {endpoint} is accessible")
                    
            except Exception as e:
                results[endpoint] = {"error": str(e)}
        
        self.results["tests"][test_name] = results
        return True
    
    def save_results(self, output_file="upload_debug_results.json"):
        """Save debug results to file"""
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        self.log(f"Debug results saved to: {output_file}")
    
    def run_debug(self, file_path):
        """Run all debug tests"""
        self.log("=" * 60)
        self.log("Starting upload debug session")
        self.log("=" * 60)
        
        # Run tests
        if not self.test_connectivity():
            self.log("Stopping tests due to connectivity failure", "ERROR")
            return
        
        self.test_ssl_certificate()
        
        if file_path and self.check_file(file_path):
            self.test_upload_endpoints()
            self.attempt_upload(file_path)
            
            # Try alternative endpoints if default fails
            if self.results["tests"].get("upload_attempt", {}).get("status") == "FAIL":
                for endpoint in ["/", "/api/upload", "/files"]:
                    self.log(f"\nTrying alternative endpoint: {endpoint}")
                    if self.attempt_upload(file_path, endpoint):
                        break
        
        self.test_server_health()
        
        # Summary
        self.log("\n" + "=" * 60)
        self.log("Debug Summary")
        self.log("=" * 60)
        
        failed_tests = [name for name, result in self.results["tests"].items() 
                       if result.get("status") == "FAIL"]
        
        if failed_tests:
            self.log(f"Failed tests: {', '.join(failed_tests)}", "ERROR")
        else:
            self.log("All tests passed!")
        
        self.save_results()


def main():
    if len(sys.argv) < 2:
        print("Usage: python debug_upload.py <file_path> [server_url]")
        print("Example: python debug_upload.py /path/to/file.zip")
        print("         python debug_upload.py /path/to/file.zip https://custom-server.com/")
        sys.exit(1)
    
    file_path = sys.argv[1]
    server_url = sys.argv[2] if len(sys.argv) > 2 else "https://stall10n.onrender.com/"
    
    debugger = UploadDebugger(server_url)
    debugger.run_debug(file_path)


if __name__ == "__main__":
    main()