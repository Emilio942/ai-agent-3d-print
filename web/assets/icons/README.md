# PWA Icons

This directory should contain the PWA icons referenced in the manifest.json file:

- icon-72.png (72x72px)
- icon-96.png (96x96px) 
- icon-128.png (128x128px)
- icon-144.png (144x144px)
- icon-152.png (152x152px)
- icon-192.png (192x192px)
- icon-384.png (384x384px)
- icon-512.png (512x512px)

For development, you can create these icons from the following SVG template:

```svg
<svg width="512" height="512" viewBox="0 0 512 512" xmlns="http://www.w3.org/2000/svg">
  <rect width="512" height="512" fill="#2563eb"/>
  <text x="256" y="280" text-anchor="middle" fill="white" font-family="Arial" font-size="120" font-weight="bold">🖨️</text>
  <text x="256" y="350" text-anchor="middle" fill="white" font-family="Arial" font-size="32">AI 3D</text>
</svg>
```

To generate the icons:
1. Save the SVG as icon.svg
2. Use an online SVG to PNG converter or tool like Inkscape
3. Export at each required size
4. Save as the corresponding PNG files

Alternative: Use a service like https://realfavicongenerator.net/ to generate all sizes from a single SVG.
