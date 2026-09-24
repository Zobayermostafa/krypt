"""
Double Random Phase Encoding - CLI tool.

Menu:
  1. Encrypt a photo             -> generates key1.txt, key2.txt, and ONE
                                     encrypted PNG (all 3 color channels
                                     stored inside it)
  2. Decrypt a photo             -> requires the exact key1.txt and key2.txt
                                     from step 1
  3. Verify a decrypted photo    -> uses difference blending (see
                                     difference.py) to objectively check
                                     whether a decrypted photo really matches
                                     the original, instead of just eyeballing it

COLOR SUPPORT
-------------
A photo has three color channels (red, green, blue). DRPE's math only
works on a single 2D array at a time, so we encrypt each channel
separately (reusing the same pair of phase-key masks for all three).
Rather than producing three separate files, drpe.py stores all three as
frames of a single animated PNG (APNG) - so the encrypted file opens at
exactly the original photo's width and height.
"""

import os
import sys

import numpy as np
from PIL import Image

from drpe import (
    generate_random_phase_mask,
    encrypt,
    decrypt,
    save_phase_mask_text,
    load_phase_mask_text,
    save_color_ciphertext_png,
    load_color_ciphertext_png,
)
from difference import (
    load_color_for_comparison,
    compute_difference,
    summarize_difference,
    save_difference_image,
)


# ---------------------------------------------------------------------------
# File I/O helpers
# ---------------------------------------------------------------------------

def prompt_existing_path(message):
    """Ask for a file path and keep asking until it actually exists."""
    while True:
        path = input(message).strip().strip('"')
        if os.path.isfile(path):
            return path
        print(f"  File not found: {path}\n")


def load_color_image(path):
    """Load an image as a float64 RGB array of shape (height, width, 3)."""
    img = Image.open(path).convert("RGB")
    return np.array(img, dtype=np.float64)


def save_color_image(rgb_array, path):
    """Clip/convert a float (height, width, 3) array to an 8-bit RGB PNG."""
    clipped = np.clip(rgb_array, 0, 255).astype(np.uint8)
    Image.fromarray(clipped, mode="RGB").save(path)


def default_output_path(input_path, suffix):
    """e.g. photo.png -> photo_encrypted.png"""
    base, _ = os.path.splitext(input_path)
    return f"{base}_{suffix}.png"


def default_key_path(input_path, key_name):
    """e.g. photo.png -> photo_key1.txt"""
    base, _ = os.path.splitext(input_path)
    return f"{base}_{key_name}.txt"


# ---------------------------------------------------------------------------
# Option 1: Encrypt
# ---------------------------------------------------------------------------

def option_encrypt():
    print("\n--- Encrypt a photo ---")
    input_path = prompt_existing_path("Path to the image you want to encrypt: ")

    image = load_color_image(input_path)  # shape: (height, width, 3)
    channel_shape = image.shape[:2]

    # One pair of secret phase-key masks, shared across all three color
    # channels (this is the actual encryption key).
    mask1 = generate_random_phase_mask(channel_shape)
    mask2 = generate_random_phase_mask(channel_shape)

    ciphertexts = [
        encrypt(image[:, :, i], mask1, mask2)
        for i in range(3)  # red, green, blue, in that order
    ]

    encrypted_path = default_output_path(input_path, "encrypted")
    key1_path = default_key_path(input_path, "key1")
    key2_path = default_key_path(input_path, "key2")

    save_color_ciphertext_png(ciphertexts, encrypted_path)
    save_phase_mask_text(mask1, key1_path)
    save_phase_mask_text(mask2, key2_path)

    print("\nDone. Files created:")
    print(f"  Encrypted image: {encrypted_path}   <- looks like pure noise, safe to share")
    print(f"  Secret key 1:    {key1_path}   (plain text file)")
    print(f"  Secret key 2:    {key2_path}   (plain text file)")
    print("\nIMPORTANT: keep key1 and key2 private. BOTH are required to decrypt.")


# ---------------------------------------------------------------------------
# Option 2: Decrypt with the correct key pair
# ---------------------------------------------------------------------------

def option_decrypt():
    print("\n--- Decrypt a photo ---")
    encrypted_path = prompt_existing_path("Path to the encrypted (.png) image: ")
    key1_path = prompt_existing_path("Path to key1.txt: ")
    key2_path = prompt_existing_path("Path to key2.txt: ")

    ciphertexts = load_color_ciphertext_png(encrypted_path)
    mask1 = load_phase_mask_text(key1_path)
    mask2 = load_phase_mask_text(key2_path)

    if mask1.shape != ciphertexts[0].shape or mask2.shape != ciphertexts[0].shape:
        print("\nError: key size doesn't match the encrypted image size. "
              "Make sure you're using the keys that were generated with THIS "
              "specific encrypted file.")
        return

    recovered_channels = [decrypt(ct, mask1, mask2) for ct in ciphertexts]
    recovered_image = np.stack(recovered_channels, axis=-1)  # (h, w, 3)

    output_path = default_output_path(encrypted_path.replace("_encrypted", ""), "decrypted")
    save_color_image(recovered_image, output_path)

    print(f"\nDone. Decrypted image saved to: {output_path}")


# ---------------------------------------------------------------------------
# Option 3: Verify a decrypted photo against the original (difference blending)
# ---------------------------------------------------------------------------

# How different two images can be, on average, and still count as a real
# match. Measured empirically: a genuine match (even after normal 8-bit
# rounding) scores well under 1; a wrong key produces a mean difference
# around 50+ with the vast majority of pixels changed. 5 gives a
# comfortable safety margin either way.
MEAN_DIFFERENCE_THRESHOLD = 5


def option_verify():
    print("\n--- Verify a decrypted photo against the original ---")
    print("This uses difference blending (see difference.py) - subtracting")
    print("the two images pixel by pixel - to check objectively whether they")
    print("really match, rather than just looking at them.\n")

    original_path = prompt_existing_path("Path to the ORIGINAL photo: ")
    decrypted_path = prompt_existing_path("Path to the photo you want to check: ")

    original = load_color_for_comparison(original_path)
    decrypted = load_color_for_comparison(decrypted_path)

    if original.shape != decrypted.shape:
        print("\nThese images are different sizes, so they can't be the same photo.")
        return

    difference = compute_difference(original, decrypted)
    mean_difference, max_difference, percent_changed = summarize_difference(difference)

    diff_output_path = default_output_path(decrypted_path, "difference")
    save_difference_image(difference, diff_output_path)

    print(f"\nMean pixel difference: {mean_difference:.2f}  (0 = identical)")
    print(f"Largest single pixel difference: {max_difference:.0f}")
    print(f"Pixels noticeably changed: {percent_changed:.1f}%")
    print(f"Difference image saved to: {diff_output_path}")
    print("(almost solid black = match; bright and noisy = mismatch)")

    if mean_difference < MEAN_DIFFERENCE_THRESHOLD:
        print("\nVERIFIED: this is the same photo (difference is negligible rounding noise).")
    else:
        print("\nNOT VERIFIED: substantial differences found. This usually means the")
        print("wrong key was used to decrypt, or these are simply different photos.")


# ---------------------------------------------------------------------------
# Main menu loop
# ---------------------------------------------------------------------------

def main():
    print("=" * 50)
    print(" Double Random Phase Encoding (DRPE) - CLI Tool")
    print("=" * 50)

    while True:
        print("\nWhat would you like to do?")
        print("  1. Encrypt a photo")
        print("  2. Decrypt a photo")
        print("  3. Verify a decrypted photo against the original")
        print("  4. Quit")

        choice = input("\nEnter 1-4: ").strip()

        try:
            if choice == "1":
                option_encrypt()
            elif choice == "2":
                option_decrypt()
            elif choice == "3":
                option_verify()
            elif choice == "4":
                print("Goodbye.")
                sys.exit(0)
            else:
                print("Please enter 1, 2, 3, or 4.")
        except Exception as e:
            print(f"\nSomething went wrong: {e}")


if __name__ == "__main__":
    main()
