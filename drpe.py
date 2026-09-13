"""
Double Random Phase Encoding (DRPE)

WHAT THIS FILE CONTAINS
------------------------
1. The actual DRPE algorithm: encrypt() and decrypt().
2. File I/O helpers that turn the algorithm's outputs into real files:
     - a phase mask (the "key")   -> a plain text (.txt) file
     - the ciphertext (complex)   -> a single PNG image

WHY FILE STORAGE NEEDS EXTRA WORK
-----------------------------------
A phase mask is an array of ANGLES (0 to 2*pi) - a text file stores that
easily. But the ciphertext is COMPLEX-valued (it has both a magnitude and
a phase at every pixel), and an ordinary image channel only stores a
single 0-255 number. To fit a complex value into an image without losing
too much precision, we split it into 16 bits of magnitude and 16 bits of
phase, then split each of those 16-bit numbers across two 8-bit channels.
The result is one RGBA PNG that reconstructs almost perfectly.
"""

import base64

import numpy as np
from PIL import Image
from PIL.PngImagePlugin import PngInfo


TWO_PI = 2 * np.pi

# We quantize angles/magnitudes into 16-bit integers (0-65535) before
# saving, which keeps files small while still being precise enough that
# the quantization error is invisible in the final image.
UINT16_MAX = 65535


# ===========================================================================
# 1. THE ALGORITHM ITSELF
# ===========================================================================

def generate_random_phase_mask(shape, seed=None):
    """
    Create a random phase mask: a complex array where every value has
    magnitude 1 and a uniformly random angle. This IS the secret key -
    without the exact angles used here, decryption is impossible.

    Pass `seed` to get a reproducible (non-secret) mask, e.g. for testing.
    """
    rng = np.random.default_rng(seed)
    random_angles = rng.uniform(0, TWO_PI, size=shape)
    return np.exp(1j * random_angles)


def encrypt(image, mask1, mask2):
    """
    Encrypt a real-valued grayscale image into complex-valued ciphertext.

        1. multiply the image by the first phase mask   (spatial domain)
        2. take the 2D Fourier transform
        3. multiply by the second phase mask             (frequency domain)
        4. inverse Fourier transform back to an image-shaped array

    The result looks like pure noise but is fully invertible with the
    same two masks.
    """
    masked_image = image * mask1
    spectrum = np.fft.fft2(masked_image)
    masked_spectrum = spectrum * mask2
    ciphertext = np.fft.ifft2(masked_spectrum)
    return ciphertext


def decrypt(ciphertext, mask1, mask2):
    """
    Reverse encrypt() exactly, by undoing each step with a conjugate mask
    (conjugate cancels a phase-only mask: mask * conj(mask) == 1).

    If either mask is even slightly wrong, this cancellation fails and
    the output is noise instead of the original image.
    """
    spectrum = np.fft.fft2(ciphertext)
    unmasked_spectrum = spectrum * np.conj(mask2)
    masked_image = np.fft.ifft2(unmasked_spectrum)
    image = masked_image * np.conj(mask1)

    return np.real(image)


# ===========================================================================
# 2. SHARED QUANTIZATION HELPERS
# ===========================================================================
# Both the key-mask file format and the ciphertext file format need to
# convert a float value into a 16-bit integer and back. These two
# functions do that one job, so the logic only needs to be correct once.

def _float_range_to_uint16(values, low, high):
    """Linearly map values in [low, high] to the integer range [0, 65535]."""
    span = high - low if high > low else 1.0  # avoid divide-by-zero on flat input
    normalized = (values - low) / span
    return np.round(normalized * UINT16_MAX).astype(np.uint16)


def _uint16_to_float_range(values, low, high):
    """Inverse of _float_range_to_uint16."""
    span = high - low if high > low else 1.0
    normalized = values.astype(np.float64) / UINT16_MAX
    return normalized * span + low


def _split_into_two_bytes(values_16bit):
    """Split a uint16 array into (high_byte, low_byte), each uint8."""
    high_byte = (values_16bit >> 8).astype(np.uint8)
    low_byte = (values_16bit & 0xFF).astype(np.uint8)
    return high_byte, low_byte


def _combine_two_bytes(high_byte, low_byte):
    """Inverse of _split_into_two_bytes: reassemble a uint16 array."""
    return (high_byte.astype(np.uint16) << 8) | low_byte.astype(np.uint16)


# ===========================================================================
# 3. SAVING / LOADING A PHASE-KEY MASK AS A TEXT FILE
# ===========================================================================
#
# File format (all plain ASCII, human-readable structure):
#
#     <height> <width>
#     <base64-encoded angle data>

def save_phase_mask_text(mask, path):
    """Save a phase mask as a plain .txt key file."""
    angles = np.angle(mask) % TWO_PI
    angles_16bit = _float_range_to_uint16(angles, low=0, high=TWO_PI)

    height, width = angles_16bit.shape
    encoded_data = base64.b64encode(angles_16bit.tobytes()).decode("ascii")

    with open(path, "w") as f:
        f.write(f"{height} {width}\n")
        f.write(encoded_data)


def load_phase_mask_text(path):
    """Load a phase-key .txt file back into a complex phase mask."""
    with open(path, "r") as f:
        dimensions_line = f.readline().strip()
        encoded_data = f.read().strip()

    height, width = (int(n) for n in dimensions_line.split())
    raw_bytes = base64.b64decode(encoded_data)
    angles_16bit = np.frombuffer(raw_bytes, dtype=np.uint16).reshape(height, width)

    angles =    _uint16_to_float_range(angles_16bit, low=0, high=TWO_PI)
    return np.exp(1j * angles)


# ===========================================================================
# 4. SAVING / LOADING CIPHERTEXT AS A PNG IMAGE
# ===========================================================================
#
# Layout of each RGBA frame (one per color channel):
#   R, G  ->  magnitude, as one 16-bit number split across two 8-bit channels
#   B, A  ->  phase,     as one 16-bit number split across two 8-bit channels
#
# A color photo has three of these (red, green, blue). Instead of saving
# three separate files - or stacking them into one abnormally tall image -
# we store all three as FRAMES of a single animated PNG (APNG). The file
# opens at exactly the original photo's width and height, and each frame
# is read back out independently by seeking to it. Each channel's
# magnitude min/max (needed to undo its scaling) is stored as plain text
# metadata inside that one PNG file.

CHANNEL_NAMES = ("r", "g", "b")


def _ciphertext_to_rgba_array(ciphertext):
    """
    Convert one complex-valued 2D ciphertext array into an RGBA uint8
    array, plus the (magnitude_min, magnitude_max) needed to undo the
    magnitude scaling later.
    """
    magnitude = np.abs(ciphertext)
    phase = np.angle(ciphertext) % TWO_PI

    magnitude_min = float(magnitude.min())
    magnitude_max = float(magnitude.max())

    magnitude_16bit = _float_range_to_uint16(magnitude, magnitude_min, magnitude_max)
    phase_16bit = _float_range_to_uint16(phase, low=0, high=TWO_PI)

    mag_high, mag_low = _split_into_two_bytes(magnitude_16bit)
    phase_high, phase_low = _split_into_two_bytes(phase_16bit)

    rgba_array = np.dstack([mag_high, mag_low, phase_high, phase_low])
    return rgba_array, magnitude_min, magnitude_max


def _rgba_array_to_ciphertext(rgba_array, magnitude_min, magnitude_max):
    """Inverse of _ciphertext_to_rgba_array."""
    mag_high, mag_low = rgba_array[..., 0], rgba_array[..., 1]
    phase_high, phase_low = rgba_array[..., 2], rgba_array[..., 3]

    magnitude_16bit = _combine_two_bytes(mag_high, mag_low)
    phase_16bit = _combine_two_bytes(phase_high, phase_low)

    magnitude = _uint16_to_float_range(magnitude_16bit, magnitude_min, magnitude_max)
    phase = _uint16_to_float_range(phase_16bit, low=0, high=TWO_PI)

    return magnitude * np.exp(1j * phase)


def save_ciphertext_png(ciphertext, path):
    """Save a single complex ciphertext array as a self-contained RGBA PNG."""
    rgba_array, magnitude_min, magnitude_max = _ciphertext_to_rgba_array(ciphertext)
    img = Image.fromarray(rgba_array, mode="RGBA")

    metadata = PngInfo()
    metadata.add_text("magnitude_min", repr(magnitude_min))
    metadata.add_text("magnitude_max", repr(magnitude_max))
    img.save(path, pnginfo=metadata)


def load_ciphertext_png(path):
    """Load a single-channel encrypted PNG back into its ciphertext array."""
    img = Image.open(path)
    img.load()  # forces PIL to parse the PNG's text metadata into img.info

    magnitude_min = float(img.info.get("magnitude_min", 0.0))
    magnitude_max = float(img.info.get("magnitude_max", 1.0))

    rgba_array = np.array(img)
    return _rgba_array_to_ciphertext(rgba_array, magnitude_min, magnitude_max)


def save_color_ciphertext_png(ciphertexts, path):
    """
    Save all three color-channel ciphertexts (red, green, blue - same
    shape) as ONE PNG file, at the SAME width/height as the original
    photo, by using an animated PNG (APNG) with three frames - one per
    channel. This keeps the encrypted file visually the same size as
    the original instead of three times taller, while still letting
    each channel be read back out separately.
    """
    frames = []
    magnitude_ranges = {}

    for name, ciphertext in zip(CHANNEL_NAMES, ciphertexts):
        rgba_array, magnitude_min, magnitude_max = _ciphertext_to_rgba_array(ciphertext)
        frames.append(Image.fromarray(rgba_array, mode="RGBA"))
        magnitude_ranges[name] = (magnitude_min, magnitude_max)

    # Metadata needed to undo each frame's magnitude scaling travels
    # inside this one file, alongside the pixel data.
    metadata = PngInfo()
    for name in CHANNEL_NAMES:
        low, high = magnitude_ranges[name]
        metadata.add_text(f"{name}_magnitude_min", repr(low))
        metadata.add_text(f"{name}_magnitude_max", repr(high))

    first_frame, remaining_frames = frames[0], frames[1:]
    first_frame.save(path, save_all=True, append_images=remaining_frames, pnginfo=metadata)


def load_color_ciphertext_png(path):
    """
    Load a combined color-ciphertext PNG (as produced by
    save_color_ciphertext_png) back into a list of three complex
    ciphertext arrays, in (red, green, blue) order.
    """
    img = Image.open(path)
    img.load()

    ciphertexts = []
    for i, name in enumerate(CHANNEL_NAMES):
        img.seek(i)
        rgba_array = np.array(img.convert("RGBA"))

        magnitude_min = float(img.info[f"{name}_magnitude_min"])
        magnitude_max = float(img.info[f"{name}_magnitude_max"])
        ciphertexts.append(_rgba_array_to_ciphertext(rgba_array, magnitude_min, magnitude_max))

    return ciphertexts
