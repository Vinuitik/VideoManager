import asyncio
from pathlib import Path
from config import VIDEOS_DIR

# To add a new preset: add a key here with an ffmpeg filter string
PRESETS: dict[str, str] = {
    "boost_2x": "volume=2.0",
    "boost_3x": "volume=3.0",
    "normalize": "loudnorm",
}


async def process_video(filename: str, preset: str, overwrite: bool = False) -> str:
    input_path = Path(VIDEOS_DIR) / filename
    af_filter = PRESETS[preset]

    stem, suffix = input_path.stem, input_path.suffix
    out_name = filename if overwrite else f"{stem}_processed{suffix}"
    output_path = Path(VIDEOS_DIR) / out_name

    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-i", str(input_path), "-af", af_filter, str(output_path), "-y",
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise RuntimeError(stderr.decode())

    return out_name
