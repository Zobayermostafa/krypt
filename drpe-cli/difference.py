"""
Difference Blending (Image Subtraction) - used here to verify that a
decrypted photo really matches the original.

THE IDEA
--------
Subtract one image from another, pixel by pixel:

    difference(x, y) = |original(x, y) - decrypted(x, y)|

If the decryption used the correct key, the result should be (almost)
identical to the original, so the difference is nearly all zeros - a
mostly black image, with only a faint pattern from tiny 8-bit rounding.

If the wrong key was used, the "decrypted" image is really just
unrelated noise, so the difference is large and random everywhere -
the difference image looks like a bright, textured mess, not a
solid black image.

This is a much simpler check than phase correlation: no FFT, just
direct pixel comparison. The tradeoff is that it can't detect a
shifted-but-otherwise-correct match (DRPE decryption never produces a
shifted image, so that's not a concern here).
"""

import numpy as np
from PIL import Image


def load_color_for_comparison(path):
    """Load an image as a float64 RGB array of shape (height, width, 3)."""
    img = Image.open(path).convert("RGB")
    return np.array(img, dtype=np.float64)


def compute_difference(image1, image2):
    """
    Pixel-wise absolute difference between two same-sized images.
    Every pixel in the result is how much that pixel changed, from
    0 (identical) to 255 (completely different).
    """
    if image1.shape != image2.shape:
        raise ValueError(
            f"Images must be the same size to compare "
            f"(got {image1.shape} and {image2.shape})."
        )
    return np.abs(image1 - image2)


def summarize_difference(difference):
    """
    Turn a difference image into a few plain numbers:
      - mean_difference   : average pixel difference (0 = identical)
      - max_difference     : the single largest pixel difference
      - percent_changed    : % of pixels that differ by more than a
                              small tolerance (catches "mostly identical
                              but a few pixels are way off" cases too)
    """
    mean_difference = float(difference.mean())
    max_difference = float(difference.max())

    noticeable = difference.mean(axis=-1) > 10  # per-pixel, averaged across R/G/B
    percent_changed = float(noticeable.mean() * 100)

    return mean_difference, max_difference, percent_changed


def save_difference_image(difference, path):
    """
    Save the difference image so it can be looked at directly. A
    genuine match saves as an almost totally black image; a mismatch
    saves as a bright, noisy image.
    """
    clipped = np.clip(difference, 0, 255).astype(np.uint8)
    Image.fromarray(clipped, mode="RGB").save(path)
