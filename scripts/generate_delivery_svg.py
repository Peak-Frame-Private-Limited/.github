#!/usr/bin/env python3
"""
Generate delivery-workflow.svg with Peak Frame branding.
Symmetrically centered with exact 24px internal paddings and 28px margins.
"""

def generate_svg():
    width = 1200
    height = 200
    
    steps = [
        {"num": "01", "name": "DISCOVER", "sub": "Research &amp; Specs", "color": "#388bfd", "bg": "#121d2f"},
        {"num": "02", "name": "DESIGN", "sub": "UI/UX &amp; Systems", "color": "#a371f7", "bg": "#1f1533"},
        {"num": "03", "name": "BUILD", "sub": "Edge Architecture", "color": "#2ea043", "bg": "#13231b"},
        {"num": "04", "name": "LAUNCH", "sub": "Global CDN Deploy", "color": "#d29922", "bg": "#281e10"},
        {"num": "05", "name": "CARE", "sub": "Telemetry &amp; Care", "color": "#ff5900", "bg": "#2e160e"},
    ]
    
    svg = []
    svg.append('<?xml version="1.0" encoding="UTF-8"?>')
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Peak Frame Delivery Workflow">')
    # Background
    svg.append(f'  <rect x="0" y="0" width="{width}" height="{height}" rx="14" fill="#0d1013" stroke="none"/>')
    # Outer container matches exactly founder-activity outer card (x=28, width=1144, 28px left/right margins)
    svg.append('  <rect x="28" y="16" width="1144" height="168" rx="12" fill="#13171b" stroke="#30363c" stroke-width="1"/>')
    
    # Title row
    svg.append('  <rect x="52" y="34" width="4" height="16" rx="2" fill="#ff5900"/>')
    svg.append('  <text x="64" y="47" font-family="-apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, sans-serif" font-size="13" font-weight="700" fill="#f6f2e9" letter-spacing="1">ENGINEERING DELIVERY LIFECYCLE</text>')
    svg.append('  <text x="340" y="47" font-family="-apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, sans-serif" font-size="11" font-weight="400" fill="#8b949e">End-to-end execution from architecture to global edge delivery</text>')
    
    # 5 cards with 24px left/right inner padding and 24px equal gaps
    card_y = 66
    card_h = 96
    card_w = 200
    start_x = 52
    gap = 24
    
    for i, s in enumerate(steps):
        cx = start_x + i * (card_w + gap)
        # Connector line & arrow to next card
        if i < len(steps) - 1:
            arrow_x = cx + card_w + 3
            arrow_y = card_y + card_h // 2
            svg.append(f'    <line x1="{cx + card_w + 3}" y1="{arrow_y}" x2="{arrow_x + 12}" y2="{arrow_y}" stroke="#30363c" stroke-width="2"/>')
            svg.append(f'    <polygon points="{arrow_x + 12},{arrow_y - 4} {arrow_x + 17},{arrow_y} {arrow_x + 12},{arrow_y + 4}" fill="#ff5900"/>')
        
        # Step card
        svg.append(f'    <rect x="{cx}" y="{card_y}" width="{card_w}" height="{card_h}" rx="8" fill="{s["bg"]}" stroke="{s["color"]}" stroke-width="1.2" stroke-opacity="0.6"/>')
        # Number pill
        svg.append(f'    <rect x="{cx + 12}" y="{card_y + 12}" width="32" height="20" rx="4" fill="{s["color"]}" fill-opacity="0.2"/>')
        svg.append(f'    <text x="{cx + 28}" y="{card_y + 26}" font-family="-apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, sans-serif" font-size="11" font-weight="700" fill="{s["color"]}" text-anchor="middle">{s["num"]}</text>')
        # Title
        svg.append(f'    <text x="{cx + 14}" y="{card_y + 56}" font-family="-apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, sans-serif" font-size="15" font-weight="700" fill="#f6f2e9">{s["name"]}</text>')
        # Subtitle
        svg.append(f'    <text x="{cx + 14}" y="{card_y + 78}" font-family="-apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, sans-serif" font-size="11" font-weight="400" fill="#a5a8ac">{s["sub"]}</text>')

    svg.append('</svg>')
    return '\n'.join(svg)

if __name__ == '__main__':
    content = generate_svg()
    for name in ['delivery-workflow.svg', 'delivery-workflow-live.svg']:
        out_path = f'/Users/vijaysirohi/.gemini/antigravity-ide/scratch/github-org/profile/assets/{name}'
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(content)
    print("Generated delivery-workflow.svg and delivery-workflow-live.svg with perfect symmetry!")
