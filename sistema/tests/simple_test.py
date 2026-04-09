#!/usr/bin/env python3
print("Starting test...")

from app.main import app
print("App imported")

routes = list(app.routes)
print(f"Found {len(routes)} routes")

for route in routes:
    if hasattr(route, 'path'):
        if 'financeiro' in route.path:
            print(f"  Financeiro: {route.path}")

print("Done!")
