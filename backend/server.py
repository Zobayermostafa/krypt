"""
DRPE Web Backend - FastAPI Server

Keys are compact: encryption generates a random 256-bit key (drpe1-...) and both
phase masks are derived from it (see keys.py). No key files are stored or uploaded.

Endpoints:
  POST   /api/encrypt                          upload image -> encrypted PNG + key string
  POST   /api/decrypt                          upload encrypted PNG + key string -> decrypted image
  POST   /api/verify                           upload original + decrypted -> diff stats + diff image
  GET    /api/download/{session_id}/{filename}  stream any result file to the browser
  DELETE /api/session/{session_id}              manually clean up a session temp files
  GET    /api/health                            liveness check
"""

import re
import sys
import time
import uuid
import shutil
import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

import numpy as np
from fastapi import FastAPI, File, Form, UploadFile, HTTPException, BackgroundTasks
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError

# Make the existing CLI modules importable
CLI_DIR = Path(__file__).resolve().parent.parent / "drpe-cli"
if str(CLI_DIR) not in sys.path:
    sys.path.insert(0, str(CLI_DIR))

from drpe import (
    encrypt,
    decrypt,
    save_color_ciphertext_png,
    load_color_ciphertext_png,
)
from difference import (
    load_color_for_comparison,
    compute_difference,
    summarize_difference,
    save_difference_image,
)
from keys import generate_key_pair, format_key_pair, parse_key, derive_masks

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

UPLOADS_DIR = Path(__file__).resolve().parent / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

SESSION_TTL_SECONDS = 600
MEAN_DIFFERENCE_THRESHOLD = 5

# Upload limits (tune to your hardware)
MAX_IMAGE_BYTES = 30 * 1024 * 1024       # 30 MB per image upload
MAX_PIXELS = 8_000_000                   # ~8 MP; each channel needs complex FFTs + 2 full-size masks

# Origins allowed to call the API directly (the Vite proxy / mounted build are same-origin)
ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------
def valid_session_id(session_id: str) -> str:
    """Reject anything that is not a canonical UUID (blocks '..' and other traversal tricks)."""
    try:
        parsed = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Session not found.")
    canonical = str(parsed)
    if canonical != session_id.lower():
        raise HTTPException(status_code=404, detail="Session not found.")
    return canonical


def new_session():
    session_id = str(uuid.uuid4())
    session_dir = UPLOADS_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_id, session_dir


def remove_session_dir(session_dir: Path):
    shutil.rmtree(session_dir, ignore_errors=True)


async def delete_session_after(session_id, delay=SESSION_TTL_SECONDS):
    await asyncio.sleep(delay)
    session_dir = UPLOADS_DIR / session_id
    if session_dir.exists():
        remove_session_dir(session_dir)
        logger.info("Auto-cleaned session %s", session_id)


def sweep_expired_sessions():
    """Delete session folders older than the TTL (covers restarts that lost the timers)."""
    now = time.time()
    for child in UPLOADS_DIR.iterdir():
        try:
            if child.is_dir() and now - child.stat().st_mtime > SESSION_TTL_SECONDS:
                remove_session_dir(child)
                logger.info("Startup-cleaned expired session %s", child.name)
        except OSError:
            logger.exception("Could not clean %s", child)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    sweep_expired_sessions()
    yield


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="DRPE API",
    description="Double Random Phase Encoding image encryption/decryption service",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# IO helpers
# ---------------------------------------------------------------------------
async def save_upload(upload: UploadFile, dest: Path, max_bytes: int = MAX_IMAGE_BYTES):
    """Stream an upload to disk in chunks, enforcing a size limit."""
    size = 0
    with dest.open("wb") as fh:
        while True:
            chunk = await upload.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > max_bytes:
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large (limit {max_bytes // (1024 * 1024)} MB).",
                )
            fh.write(chunk)


def download_url(session_id, filename):
    return f"/api/download/{session_id}/{filename}"


def safe_suffix(filename):
    suffix = Path(filename or "image.png").suffix
    return suffix if re.fullmatch(r"\.[A-Za-z0-9]{1,5}", suffix or "") else ".png"


def check_pixel_limit(path: Path):
    """Read only the header to reject oversized images before decoding them."""
    with Image.open(path) as img:
        width, height = img.size
    if width * height > MAX_PIXELS:
        raise HTTPException(
            status_code=413,
            detail=f"Image too large ({width}x{height}). Limit is {MAX_PIXELS:,} pixels.",
        )


def load_color_image(path):
    img = Image.open(path).convert("RGB")
    return np.array(img, dtype=np.float64)


def save_color_image(rgb_array, path):
    clipped = np.clip(rgb_array, 0, 255).astype(np.uint8)
    Image.fromarray(clipped).save(str(path))


# Errors that mean "the user sent something unusable" rather than "the server broke"
BAD_INPUT_ERRORS = (UnidentifiedImageError, ValueError)


# ---------------------------------------------------------------------------
# CPU-bound jobs (run in a worker thread so the event loop stays responsive)
# ---------------------------------------------------------------------------
def encrypt_job(input_path: Path, session_dir: Path) -> tuple[str, str]:
    check_pixel_limit(input_path)
    img_array = load_color_image(input_path)

    seed1, seed2 = generate_key_pair()
    mask1, mask2 = derive_masks(seed1, seed2, img_array.shape[:2])
    ciphertexts = [encrypt(img_array[:, :, i], mask1, mask2) for i in range(3)]

    save_color_ciphertext_png(ciphertexts, str(session_dir / "encrypted.png"))
    return format_key_pair(seed1, seed2)


def decrypt_job(session_dir: Path, seed1: bytes, seed2: bytes):
    enc_path = session_dir / "encrypted.png"
    check_pixel_limit(enc_path)

    ciphertexts = load_color_ciphertext_png(str(enc_path))
    m1, m2 = derive_masks(seed1, seed2, ciphertexts[0].shape)

    recovered = [decrypt(ct, m1, m2) for ct in ciphertexts]
    save_color_image(np.stack(recovered, axis=-1), session_dir / "decrypted.png")


def verify_job(session_dir: Path):
    orig_path = session_dir / "original.png"
    dec_path = session_dir / "decrypted.png"
    check_pixel_limit(orig_path)
    check_pixel_limit(dec_path)

    orig_arr = load_color_for_comparison(str(orig_path))
    dec_arr = load_color_for_comparison(str(dec_path))

    if orig_arr.shape != dec_arr.shape:
        raise HTTPException(status_code=400, detail=f"Size mismatch: {orig_arr.shape} vs {dec_arr.shape}")

    difference = compute_difference(orig_arr, dec_arr)
    mean_diff, max_diff, pct_changed = summarize_difference(difference)
    save_difference_image(difference, str(session_dir / "difference.png"))
    return float(mean_diff), float(max_diff), float(pct_changed)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/encrypt")
async def api_encrypt(
    background_tasks: BackgroundTasks,
    image: UploadFile = File(..., description="Image to encrypt"),
):
    session_id, session_dir = new_session()
    input_path = session_dir / f"input{safe_suffix(image.filename)}"

    try:
        await save_upload(image, input_path)
        key1_string, key2_string = await run_in_threadpool(encrypt_job, input_path, session_dir)
    except HTTPException:
        remove_session_dir(session_dir)
        raise
    except BAD_INPUT_ERRORS as exc:
        remove_session_dir(session_dir)
        logger.warning("Encrypt rejected input: %s", exc)
        raise HTTPException(status_code=400, detail="Could not read the uploaded file as an image.")
    except Exception as exc:
        remove_session_dir(session_dir)
        logger.exception("Encrypt failed")
        raise HTTPException(status_code=500, detail=f"Encryption failed: {exc}")

    # The plaintext upload is no longer needed once encrypted.
    input_path.unlink(missing_ok=True)

    background_tasks.add_task(delete_session_after, session_id)
    return JSONResponse(
        {
            "session_id": session_id,
            "key1": key1_string,
            "key2": key2_string,
            # Maintain backward compatibility in case anything inspects 'key'
            "key": f"{key1_string}\n{key2_string}",
            "files": {"encrypted_image": download_url(session_id, "encrypted.png")},
            "message": "Encryption successful. Save both keys: without both of them the image cannot be recovered.",
        },
        headers={"Cache-Control": "no-store"},  # response contains secret keys
    )


@app.post("/api/decrypt")
async def api_decrypt(
    background_tasks: BackgroundTasks,
    encrypted_image: UploadFile = File(..., description="Encrypted .png file"),
    key1: str = Form(..., description="Key 1 string starting with drpe1-m1-"),
    key2: str = Form(..., description="Key 2 string starting with drpe1-m2-"),
):
    try:
        seed1 = parse_key(key1, expected_mask_index=1)
        seed2 = parse_key(key2, expected_mask_index=2)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid key: {exc}")

    session_id, session_dir = new_session()

    try:
        await save_upload(encrypted_image, session_dir / "encrypted.png")
        await run_in_threadpool(decrypt_job, session_dir, seed1, seed2)
    except HTTPException:
        remove_session_dir(session_dir)
        raise
    except BAD_INPUT_ERRORS as exc:
        remove_session_dir(session_dir)
        logger.warning("Decrypt rejected input: %s", exc)
        raise HTTPException(status_code=400, detail="Encrypted image is invalid or corrupted.")
    except Exception as exc:
        remove_session_dir(session_dir)
        logger.exception("Decrypt failed")
        raise HTTPException(status_code=500, detail=f"Decryption failed: {exc}")

    background_tasks.add_task(delete_session_after, session_id)
    return JSONResponse({
        "session_id": session_id,
        "files": {"decrypted_image": download_url(session_id, "decrypted.png")},
        "message": "Decryption complete. If the keys do not match this image, the result will look like noise.",
    })


@app.post("/api/verify")
async def api_verify(
    background_tasks: BackgroundTasks,
    original: UploadFile = File(..., description="Original image"),
    decrypted: UploadFile = File(..., description="Decrypted image to verify"),
):
    session_id, session_dir = new_session()

    try:
        await save_upload(original, session_dir / "original.png")
        await save_upload(decrypted, session_dir / "decrypted.png")
        mean_diff, max_diff, pct_changed = await run_in_threadpool(verify_job, session_dir)
    except HTTPException:
        remove_session_dir(session_dir)
        raise
    except BAD_INPUT_ERRORS as exc:
        remove_session_dir(session_dir)
        logger.warning("Verify rejected input: %s", exc)
        raise HTTPException(status_code=400, detail="Could not read one of the uploaded files as an image.")
    except Exception as exc:
        remove_session_dir(session_dir)
        logger.exception("Verify failed")
        raise HTTPException(status_code=500, detail=f"Verification failed: {exc}")

    background_tasks.add_task(delete_session_after, session_id)
    verified = mean_diff < MEAN_DIFFERENCE_THRESHOLD
    return JSONResponse({
        "session_id": session_id,
        "verified": verified,
        "stats": {
            "mean_difference": round(mean_diff, 4),
            "max_difference": round(max_diff, 4),
            "percent_changed": round(pct_changed, 2),
        },
        "files": {"difference_image": download_url(session_id, "difference.png")},
        "message": (
            "VERIFIED: Images match (negligible rounding noise)."
            if verified else
            "NOT VERIFIED: Substantial differences found."
        ),
    })


@app.get("/api/download/{session_id}/{filename}")
async def api_download(session_id: str, filename: str):
    session_id = valid_session_id(session_id)
    safe_name = Path(filename).name
    file_path = UPLOADS_DIR / session_id / safe_name
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found or session expired.")
    media_types = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".txt": "text/plain"}
    media_type = media_types.get(file_path.suffix.lower(), "application/octet-stream")
    return FileResponse(path=str(file_path), media_type=media_type, filename=safe_name)


@app.delete("/api/session/{session_id}")
async def api_delete_session(session_id: str):
    session_id = valid_session_id(session_id)
    session_dir = UPLOADS_DIR / session_id
    if session_dir.is_dir():
        remove_session_dir(session_dir)
        return {"message": f"Session {session_id} deleted."}
    raise HTTPException(status_code=404, detail="Session not found.")


# ---------------------------------------------------------------------------
# Mount compiled frontend UI (if built)
# ---------------------------------------------------------------------------
DIST_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if (DIST_DIR / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(DIST_DIR), html=True), name="frontend")
