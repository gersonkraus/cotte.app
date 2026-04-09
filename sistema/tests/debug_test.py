#!/usr/bin/env python3

with open('debug_output.txt', 'w') as f:
    f.write("Starting test...\n")
    
    from app.main import app
    f.write("App imported\n")
    
    routes = list(app.routes)
    f.write(f"Found {len(routes)} routes\n")
    
    for route in routes:
        if hasattr(route, 'path'):
            if 'financeiro' in route.path:
                f.write(f"  Financeiro: {route.path}\n")
    
    f.write("Done!\n")
