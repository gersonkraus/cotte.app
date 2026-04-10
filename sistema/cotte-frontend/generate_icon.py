import urllib.request
import json
import base64

# Generate a base64 encoded 512x512 placeholder PNG
# We'll just create a solid blue image with PNG header
# Or use python's PIL if available
try:
    from PIL import Image, ImageDraw
    img = Image.new('RGB', (512, 512), color = '#2563eb')
    d = ImageDraw.Draw(img)
    img.save('/home/gk/Projeto-izi/sistema/cotte-frontend/icon-512x512.png')
    print("Success using PIL")
except ImportError:
    print("PIL not found")
