#!/usr/bin/env python3
"""Test if the categorias endpoint is properly registered"""

from app.main import app
from fastapi.routing import APIRoute

def check_endpoint():
    """Check if /financeiro/categorias endpoint exists"""
    
    # Get all routes
    routes = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            routes.append(f"{route.methods} {route.path}")
    
    print(f"Total routes found: {len(routes)}")
    
    # Check for categorias endpoint
    categorias_found = False
    for route in routes:
        if "categorias" in route and "/financeiro/" in route:
            print(f"✅ Found categorias endpoint: {route}")
            categorias_found = True
    
    if not categorias_found:
        print("❌ /financeiro/categorias endpoint not found")
        print("\nFinanceiro endpoints found:")
        for route in routes:
            if "/financeiro/" in route:
                print(f"  {route}")
    
    return categorias_found

if __name__ == "__main__":
    result = check_endpoint()
    print(f"\nResult: {'SUCCESS' if result else 'FAILED'}")
