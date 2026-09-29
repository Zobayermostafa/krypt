# DRPE Image Encryption Suite

A web application for encrypting, decrypting, and verifying color images with
Double Random Phase Encoding (DRPE). The project combines a React/Vite
frontend with a FastAPI backend and the original NumPy/Pillow DRPE engine.

DRPE applies independent phase masks in the spatial and Fourier domains. The
result is a noise-like encrypted PNG that can only be reconstructed with both
secret keys generated for that image.

## Features

- **Encrypt:** Upload a photo and receive an encrypted PNG plus two independent
  43-character keys.
- **Decrypt:** Upload the encrypted PNG and provide both keys to reconstruct the
  image.
- **Verify:** Compare an original image with a decrypted image using a
  pixel-wise difference map and summary statistics.
- **RGB support:** Red, green, and blue channels are processed independently
  and stored together in the encrypted PNG format.
- **Temporary sessions:** Uploaded and generated files are stored in a session
  directory and automatically removed after 10 minutes.
- **Responsive web UI:** Switch between Encrypt, Decrypt, and Verify workflows
  from one browser-based dashboard.

## Requirements

- Python 3.10 or newer
- Node.js and npm
- Windows users can use the included `start.bat` launcher.

The backend accepts images up to 30 MB and approximately 8 megapixels. Larger
uploads are rejected before processing.

## Quick Start

### Windows launcher

Create a Python virtual environment, install the backend dependencies, install
the frontend dependencies, and then run the launcher:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
cd frontend
npm install
cd ..
start.bat
```

The launcher opens two terminal windows and starts:

- Web UI: <http://localhost:5173>
- Backend API: <http://localhost:8000>
- Swagger API docs: <http://localhost:8000/docs>

The included launcher expects the virtual environment at `.venv` and uses a
local Node.js installation when available. If its configured Node.js path does
not exist, make sure `node` and `npm` are available on `PATH`.

### Run manually

Start the backend from the repository root:

```powershell
.venv\Scripts\python.exe -m uvicorn backend.server:app --reload --host 0.0.0.0 --port 8000
```

In a second terminal, start the frontend:

```powershell
cd frontend
npm run dev
```

Open <http://localhost:5173> after both services are running.

## Using the Web App

1. Open the **Encrypt** workflow and upload a photo.
2. Download the encrypted PNG and save both generated keys. The keys are not
   stored on the server; losing either key makes recovery impossible.
3. Open **Decrypt**, upload the encrypted PNG, and enter both keys. A key file
   saved by the Encrypt workflow can also be loaded automatically.
4. Open **Verify**, upload the original and decrypted images, and review the
   match verdict, difference statistics, and downloadable difference map.

Verification considers images with a mean pixel difference below `5` to be a
match. A black difference map indicates that the images are equal apart from
small rounding noise; bright areas indicate mismatches.

## API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Check backend availability |
| `POST` | `/api/encrypt` | Upload an image and generate ciphertext plus two keys |
| `POST` | `/api/decrypt` | Upload ciphertext and `key1`/`key2` form fields |
| `POST` | `/api/verify` | Upload `original` and `decrypted` images for comparison |
| `GET` | `/api/download/{session_id}/{filename}` | Download a generated result |
| `DELETE` | `/api/session/{session_id}` | Remove a session immediately |

Interactive request and response schemas are available at
<http://localhost:8000/docs> while the backend is running.

## Project Structure

```text
backend/
  keys.py              Key generation and deterministic phase-mask derivation
  server.py            FastAPI routes, validation, sessions, and file downloads
  main.py              Optional backend entry point
  requirements.txt     Backend dependencies
drpe-cli/
  drpe.py              DRPE FFT encryption/decryption engine
  difference.py        Pixel difference and verification helpers
  main.py              Original command-line interface
frontend/
  src/App.tsx          React dashboard and workflow navigation
  src/components/      Encrypt, decrypt, verify, and shared UI components
  package.json          Frontend scripts and dependencies
start.bat              Windows launcher for frontend and backend
```

## Security Notes

- Each encryption operation generates two independent 256-bit secret seeds.
- Keys are returned only in the encryption response and are not persisted by
  the backend.
- Use HTTPS and a trusted deployment environment before exposing the service
  beyond a local development machine.
- This project demonstrates DRPE image transformation. It should not be
  treated as a replacement for a peer-reviewed, authenticated encryption
  scheme when strong confidentiality or tamper detection is required.