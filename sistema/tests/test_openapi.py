#!/usr/bin/env python3
"""Test script to check if /financeiro/categorias endpoint is in OpenAPI spec"""

import requests
import json

def test_openapi_spec():
    """Check if categorias endpoint is in OpenAPI spec"""
    url = "http://localhost:8000/openapi.json"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            spec = response.json()
            
            # Check if the endpoint exists
            paths = spec.get('paths', {})
            categorias_path = paths.get('/financeiro/categorias')
            
            if categorias_path:
                print("✅ /financeiro/categorias endpoint found in OpenAPI spec!")
                get_method = categorias_path.get('get')
                if get_method:
                    print(f"   Method: GET")
                    print(f"   Summary: {get_method.get('summary', 'N/A')}")
                    responses = get_method.get('responses', {})
                    print(f"   Responses: {list(responses.keys())}")
                return True
            else:
                print("❌ /financeiro/categorias endpoint NOT found in OpenAPI spec")
                print(f"Available financeiro paths:")
                for path in paths:
                    if '/financeiro/' in path:
                        print(f"   - {path}")
                return False
        else:
            print(f"❌ Failed to get OpenAPI spec: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_openapi_spec()
