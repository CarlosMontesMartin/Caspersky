"""QR."""
import base64
import io

import qrcode


def generar_qr(url: str) -> str:
    """PNG del QR como data URL: data:image/png;base64,..."""
    buffer = io.BytesIO()
    qrcode.make(url).save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()
