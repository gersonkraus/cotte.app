#!/usr/bin/env python3
"""Test script to check if /financeiro/categorias endpoint works"""

import requests
import json

def test_categorias_endpoint():
    """Test the /financeiro/categorias endpoint"""
    url = "http://localhost:8000/financeiro/categorias"
    
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Success! Found {len(data)} categories")
            for cat in data[:3]:  # Show first 3 categories
                print(f"  - {cat['nome']} (tipo: {cat['tipo']})")
        else:
            print(f"Error: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("Connection error - server might not be running")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_categorias_endpoint()
