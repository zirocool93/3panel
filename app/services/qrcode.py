from base64 import b64encode
from io import BytesIO
from urllib.parse import quote


def qr_png_data_url(value: str) -> str:
    try:
        import qrcode
    except ImportError:
        return _fallback_svg_data_url(value)
    image = qrcode.make(value)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return f"data:image/png;base64,{b64encode(buffer.getvalue()).decode('ascii')}"


def _fallback_svg_data_url(value: str) -> str:
    escaped = (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="220" height="220">'
        '<rect width="220" height="220" fill="white"/>'
        '<text x="12" y="24" font-family="Arial" font-size="12" fill="black">'
        "QR package is not installed"
        "</text>"
        f'<text x="12" y="48" font-family="Arial" font-size="10" fill="black">{escaped}</text>'
        "</svg>"
    )
    return f"data:image/svg+xml,{quote(svg)}"
