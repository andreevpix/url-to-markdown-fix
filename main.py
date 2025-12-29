from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from markitdown import MarkItDown, UnsupportedFormatException, FileConversionException
from urllib.parse import unquote
import asyncio
import logging
import re

app = FastAPI(
title="URL to Markdown API",
description="API service to convert urls to markdown using MarkItDown",
version="1.0.0",
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def normalize_url(url: str) -> str:
# Fix protocol: http:/example.com -> http://example.com
url = re.sub(r'^(https?):/?(?!/)', r'\1://', url)
# Add https:// if no protocol
if not url.startswith(("http://", "https://")):
    if url.startswith("www."):
        url = "https://" + url
    else:
        url = "https://" + url
return url


@app.get("/healthz")
async def healthz():
return Response(content="ok", media_type="text/plain")


@app.get("/{url:path}")
async def convert_url(url: str, request: Request):
url = (
    request.url.path[1:]
    if not request.url.query
    else request.url.path[1:] + "?" + request.url.query
)
logger.info("Received URL path: %s", url)
if url is None or url == "":
    return Response(
        content="Welcome to URL to Markdown API\nUsage: https://markdown.nimk.ir/YOUR_URL",
        media_type="text/plain",
    )

decoded_url = unquote(url)
logger.info("Decoded URL: %s", decoded_url)

try:
    decoded_url = normalize_url(decoded_url)
    logger.info("Normalized URL: %s", decoded_url)

    try:
        async def _convert() -> str:
            def _run():
                instance = MarkItDown()
                conversion_result = instance.convert(decoded_url)
                return conversion_result.text_content
            return await asyncio.to_thread(_run)

        text_content = await asyncio.wait_for(_convert(), timeout=25)
        return Response(content=text_content, media_type="text/plain")
    except UnsupportedFormatException as e:
        raise HTTPException(
            status_code=415, detail=f"Unsupported URL format: {str(e)}"
        )
    except FileConversionException as e:
        raise HTTPException(
            status_code=400, detail=f"URL conversion failed: {str(e)}"
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504, detail="Conversion timed out. Please try again later."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {str(e)}"
        )
except HTTPException:
    raise
except Exception as e:
    raise HTTPException(status_code=400, detail=f"URL processing failed: {str(e)}")
