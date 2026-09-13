# DRPE Image Encryption & Verification

A command-line Python tool for encrypting, decrypting, and verifying color images using Double Random Phase Encoding (DRPE). 

This project leverages spatial and frequency-domain image manipulation to transform regular photos into secure, complex-valued ciphertexts. By multiplying the image by a random phase mask, taking the 2D Fast Fourier Transform (FFT), and applying a second phase mask in the frequency domain, the original image is scrambled into pure noise. It is fully invertible only with the exact pair of phase keys.

---

## 🚀 Features

* **Double Random Phase Encoding:** Secures images using phase masking and 2D Fourier transforms.
* **Complex Data Storage:** Cryptographically transforms images into complex numbers (magnitude and phase), elegantly storing the 16-bit high-precision data across the color channels of a single Animated PNG (APNG) file.
* **RGB Color Support:** Processes the red, green, and blue channels independently, storing all three as separate frames within the same output file to maintain the original image dimensions.
* **Difference Blending Verification:** Uses direct pixel-wise absolute difference calculations to objectively verify that a decrypted photo matches the original, checking for rounding noise versus complete key mismatches.

---

## 🛠️ Installation

Ensure you have Python installed, then install the required dependencies:

```bash
pip install -r requirements.txt
```

The dependencies required are `numpy` for the mathematical transformations and `pillow` for image processing.

---

## 💻 Usage

Run the main interactive script to start the CLI tool:

```bash
python main.py
```

### Menu Options

1. **Encrypt a photo:** 
   You will be prompted for an image path. The script generates two plain-text key files (`_key1.txt`, `_key2.txt`) and one encrypted PNG file (`_encrypted.png`) containing all three color channels.
2. **Decrypt a photo:** 
   Provide the encrypted PNG and the exact two text key files generated during encryption. The tool will reverse the frequency-domain transformations and output the `_decrypted.png`.
3. **Verify a decrypted photo:** 
   Provide the original photo and the newly decrypted photo. The script generates a `_difference.png` file. A near-black image indicates a successful decryption, while a bright, textured mess indicates the wrong keys were used.

---

## 📂 Project Structure

* **`main.py`**
  The interactive command-line interface tying the project together. It handles file prompting, routing, and the main user loop.
* **`drpe.py`**
  The core cryptographic engine. It contains the 2D FFT encryption/decryption logic and the custom file I/O helpers required to quantize and pack complex float values into 8-bit RGBA channels.
* **`difference.py`**
  The verification module. It handles the pixel-wise subtraction and summary statistics to measure the mean pixel difference, maximum difference, and the percentage of noticeably changed pixels.
* **`requirements.txt`**
  The list of required Python packages.