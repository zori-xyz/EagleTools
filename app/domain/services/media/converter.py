# app/domain/services/media/converter.py
from __future__ import annotations

import asyncio
import shutil
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path


class ConvertError(RuntimeError):
    """Ошибка конвертации. str(e) — machine-readable код."""
    pass


@dataclass(frozen=True)
class ConvertResult:
    out_path: Path
    tmp_dir: Path


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

async def _run_ffmpeg(cmd: list[str]) -> None:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, err = await proc.communicate()
    if proc.returncode != 0:
        msg = (err or b"").decode("utf-8", errors="ignore")[:600]
        raise ConvertError(f"ffmpeg_failed:{msg}")


def _mk_tmp(workdir: Path) -> Path:
    workdir.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix="conv_", dir=str(workdir)))


def _safe_stem(filename: str, max_len: int = 60) -> str:
    stem = Path(filename).stem
    safe = "".join(c for c in stem if c.isalnum() or c in "._- ")
    return (safe.strip() or uuid.uuid4().hex[:8])[:max_len]


def cleanup(result: ConvertResult) -> None:
    try:
        shutil.rmtree(result.tmp_dir, ignore_errors=True)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────
# Action → ffmpeg args map
# ─────────────────────────────────────────────────────────────

# action_id → (output_ext, ffmpeg_extra_args)
_AUDIO_ACTIONS: dict[str, tuple[str, list[str]]] = {
    "video_to_mp3":   ("mp3",  ["-vn", "-acodec", "libmp3lame", "-b:a", "192k"]),
    "video_to_m4a":   ("m4a",  ["-vn", "-acodec", "aac", "-b:a", "192k"]),
    "audio_to_mp3":   ("mp3",  ["-vn", "-acodec", "libmp3lame", "-b:a", "192k"]),
    "audio_to_wav":   ("wav",  ["-vn", "-acodec", "pcm_s16le"]),
    "audio_to_ogg":   ("ogg",  ["-vn", "-acodec", "libvorbis", "-q:a", "4"]),
    "audio_to_m4a":   ("m4a",  ["-vn", "-acodec", "aac", "-b:a", "192k"]),
}

_VIDEO_ACTIONS: dict[str, tuple[str, list[str]]] = {
    "video_to_mp4":   ("mp4",  ["-c:v", "libx264", "-crf", "23", "-preset", "fast",
                                 "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart"]),
}

_COMPRESS_ACTIONS: dict[str, tuple[str, list[str]]] = {
    "video_compress": ("mp4",  ["-c:v", "libx264", "-crf", "28", "-preset", "fast",
                                 "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart"]),
    "audio_compress": ("mp3",  ["-vn", "-acodec", "libmp3lame", "-b:a", "96k"]),
}

_GIF_ACTIONS: set[str] = {"video_to_gif"}


# ─────────────────────────────────────────────────────────────
# Max duration guard (секунды) — защита от злоупотреблений
# ─────────────────────────────────────────────────────────────
MAX_DURATION_FREE    = 600   # 10 мин
MAX_DURATION_PREMIUM = 7200  # 2 часа


async def _get_duration(path: Path) -> float | None:
    """ffprobe — длительность в секундах."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffprobe", "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        out, _ = await proc.communicate()
        return float(out.decode().strip())
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────

async def convert_file(
    in_path: Path,
    *,
    action: str,
    workdir: Path,
    is_premium: bool = False,
    timeout_sec: int = 300,
) -> ConvertResult:
    """
    Конвертирует файл согласно action.
    Возвращает ConvertResult(out_path, tmp_dir).
    Вызывающий код должен вызвать cleanup() после отдачи файла.
    """
    if not in_path.exists() or not in_path.is_file():
        raise ConvertError("input_missing")

    action = action.strip().lower()
    tmp_dir = _mk_tmp(workdir)

    # Проверяем длительность для медиа
    if action in {*_AUDIO_ACTIONS, *_VIDEO_ACTIONS, *_COMPRESS_ACTIONS, *_GIF_ACTIONS}:
        duration = await _get_duration(in_path)
        if duration is not None:
            max_dur = MAX_DURATION_PREMIUM if is_premium else MAX_DURATION_FREE
            if duration > max_dur:
                shutil.rmtree(tmp_dir, ignore_errors=True)
                raise ConvertError("duration_exceeded")

    try:
        result = await asyncio.wait_for(
            _do_convert(in_path, action=action, tmp_dir=tmp_dir),
            timeout=timeout_sec,
        )
    except asyncio.TimeoutError:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise ConvertError("timeout")
    except ConvertError:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise
    except Exception as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise ConvertError(f"unexpected:{e}") from e

    return result


async def _do_convert(in_path: Path, *, action: str, tmp_dir: Path) -> ConvertResult:
    stem = _safe_stem(in_path.name)

    # ── Аудио из видео / конвертация аудио ──────────────────
    if action in _AUDIO_ACTIONS:
        ext, extra = _AUDIO_ACTIONS[action]
        out = tmp_dir / f"{stem}.{ext}"
        await _run_ffmpeg(["ffmpeg", "-y", "-i", str(in_path), *extra, str(out)])
        _check_out(out)
        return ConvertResult(out_path=out, tmp_dir=tmp_dir)

    # ── Конвертация видео ────────────────────────────────────
    if action in _VIDEO_ACTIONS:
        ext, extra = _VIDEO_ACTIONS[action]
        out = tmp_dir / f"{stem}.{ext}"
        await _run_ffmpeg(["ffmpeg", "-y", "-i", str(in_path), *extra, str(out)])
        _check_out(out)
        return ConvertResult(out_path=out, tmp_dir=tmp_dir)

    # ── Сжатие ──────────────────────────────────────────────
    if action in _COMPRESS_ACTIONS:
        ext, extra = _COMPRESS_ACTIONS[action]
        out = tmp_dir / f"{stem}_compressed.{ext}"
        await _run_ffmpeg(["ffmpeg", "-y", "-i", str(in_path), *extra, str(out)])
        _check_out(out)
        return ConvertResult(out_path=out, tmp_dir=tmp_dir)

    # ── GIF ─────────────────────────────────────────────────
    if action == "video_to_gif":
        out = tmp_dir / f"{stem}.gif"
        # Palette для качественного GIF
        palette = tmp_dir / "palette.png"
        await _run_ffmpeg([
            "ffmpeg", "-y", "-i", str(in_path),
            "-vf", "fps=10,scale=480:-1:flags=lanczos,palettegen",
            str(palette),
        ])
        await _run_ffmpeg([
            "ffmpeg", "-y", "-i", str(in_path), "-i", str(palette),
            "-lavfi", "fps=10,scale=480:-1:flags=lanczos[x];[x][1:v]paletteuse",
            str(out),
        ])
        _check_out(out)
        return ConvertResult(out_path=out, tmp_dir=tmp_dir)

    # ── STT (аудио → текст) ──────────────────────────────────
    if action in {"audio_stt", "video_stt"}:
        # Сначала извлекаем аудио если это видео
        if action == "video_stt":
            audio_tmp = tmp_dir / f"{stem}_audio.mp3"
            await _run_ffmpeg([
                "ffmpeg", "-y", "-i", str(in_path),
                "-vn", "-acodec", "libmp3lame", "-b:a", "128k",
                str(audio_tmp),
            ])
            stt_input = audio_tmp
        else:
            stt_input = in_path

        from app.domain.services.media.stt import transcribe_to_text, SttError
        from app.common.config import settings
        model_dir = Path(settings.data_dir) / "models" / "whisper"
        try:
            stt_result = await transcribe_to_text(
                stt_input, workdir=tmp_dir, model_dir=model_dir, timeout_sec=180,
            )
        except SttError as e:
            raise ConvertError(f"stt_failed:{e}") from e

        out = tmp_dir / f"{stem}.txt"
        out.write_text(stt_result.text, encoding="utf-8")
        _check_out(out)
        return ConvertResult(out_path=out, tmp_dir=tmp_dir)

    # ── Изображения ─────────────────────────────────────────
    if action in {"img_to_jpg", "img_to_png", "img_to_webp", "img_compress"}:
        return await _do_image(in_path, action=action, tmp_dir=tmp_dir)

    # ── PDF ─────────────────────────────────────────────────
    if action in {"pdf_to_txt", "pdf_to_img", "pdf_compress"}:
        return await _do_pdf(in_path, action=action, tmp_dir=tmp_dir)

    # ── Документы ────────────────────────────────────────────
    if action in {"doc_to_pdf", "doc_to_txt"}:
        return await _do_document(in_path, action=action, tmp_dir=tmp_dir)

    raise ConvertError(f"unknown_action:{action}")


async def _do_image(in_path: Path, *, action: str, tmp_dir: Path) -> ConvertResult:
    """Конвертация изображений через Pillow."""
    try:
        from PIL import Image
    except ImportError:
        raise ConvertError("pillow_missing")

    # HEIC/HEIF — конвертируем через ffmpeg в PNG сначала
    in_ext = in_path.suffix.lower().lstrip(".")
    if in_ext in ("heic", "heif"):
        png_tmp = tmp_dir / f"{in_path.stem}_conv.png"
        await _run_ffmpeg(["ffmpeg", "-y", "-i", str(in_path), str(png_tmp)])
        if png_tmp.exists() and png_tmp.stat().st_size > 0:
            in_path = png_tmp
        else:
            raise ConvertError("heic_convert_failed")

    stem = _safe_stem(in_path.name)

    ext_map = {
        "img_to_jpg":     ("jpg",  "JPEG"),
        "img_to_png":     ("png",  "PNG"),
        "img_to_webp":    ("webp", "WEBP"),
        "img_compress":   ("jpg",  "JPEG"),
    }

    # jpg и jpeg — одно и то же
    in_ext = in_path.suffix.lower().lstrip(".")
    if in_ext == "jpeg":
        in_ext = "jpg"
    # Если конвертируем в тот же формат — просто сжимаем
    out_ext = ext_map[action][0]
    if in_ext == out_ext and action != "img_compress":
        action = "img_compress"

    ext, fmt = ext_map[action]
    out = tmp_dir / f"{stem}.{ext}"

    try:
        img = Image.open(str(in_path))

        # Конвертируем RGBA/P в RGB для JPEG
        if fmt == "JPEG" and img.mode in ("RGBA", "P", "LA"):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            bg.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
            img = bg
        elif img.mode not in ("RGB", "RGBA", "L") and fmt != "JPEG":
            img = img.convert("RGB")

        save_kwargs = {}
        if fmt == "JPEG":
            # compress = сильнее сжимаем, иначе стандартное качество
            quality = 60 if action == "img_compress" else 85
            save_kwargs = {"quality": quality, "optimize": True}
        elif fmt == "WEBP":
            save_kwargs = {"quality": 82, "method": 4}
        elif fmt == "PNG":
            save_kwargs = {"optimize": True}

        img.save(str(out), fmt, **save_kwargs)

    except ConvertError:
        raise
    except Exception as e:
        raise ConvertError(f"image_failed:{e}")

    _check_out(out)
    return ConvertResult(out_path=out, tmp_dir=tmp_dir)


async def _do_pdf(in_path: Path, *, action: str, tmp_dir: Path) -> ConvertResult:
    """PDF операции."""
    stem = _safe_stem(in_path.name)

    if action == "pdf_to_txt":
        # Извлекаем текст через pdfminer или pymupdf
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(str(in_path))
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
        except ImportError:
            raise ConvertError("pymupdf_missing")
        except Exception as e:
            raise ConvertError(f"pdf_failed:{e}")

        out = tmp_dir / f"{stem}.txt"
        out.write_text(text.strip(), encoding="utf-8")
        _check_out(out)
        return ConvertResult(out_path=out, tmp_dir=tmp_dir)

    if action == "pdf_to_img":
        # Конвертируем страницы в PNG через PyMuPDF
        try:
            import fitz
            doc = fitz.open(str(in_path))
            # Берём первую страницу
            page = doc[0]
            mat = fitz.Matrix(2.0, 2.0)  # 2x zoom = хорошее качество
            pix = page.get_pixmap(matrix=mat)
            doc.close()
        except ImportError:
            raise ConvertError("pymupdf_missing")
        except Exception as e:
            raise ConvertError(f"pdf_failed:{e}")

        out = tmp_dir / f"{stem}_page1.png"
        pix.save(str(out))
        _check_out(out)
        return ConvertResult(out_path=out, tmp_dir=tmp_dir)

    if action == "pdf_compress":
        # Сжимаем PDF через ghostscript если есть, иначе ffmpeg
        out = tmp_dir / f"{stem}_compressed.pdf"
        try:
            proc = await asyncio.create_subprocess_exec(
                "gs", "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.4",
                "-dPDFSETTINGS=/ebook", "-dNOPAUSE", "-dQUIET", "-dBATCH",
                f"-sOutputFile={out}", str(in_path),
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            _, err = await proc.communicate()
            if proc.returncode != 0:
                raise ConvertError("gs_failed")
        except FileNotFoundError:
            raise ConvertError("ghostscript_missing")
        _check_out(out)
        return ConvertResult(out_path=out, tmp_dir=tmp_dir)

    raise ConvertError(f"unknown_pdf_action:{action}")


async def _do_document(in_path: Path, *, action: str, tmp_dir: Path) -> ConvertResult:
    """Документы через LibreOffice."""
    stem = _safe_stem(in_path.name)

    # Находим LibreOffice
    import shutil
    lo_bin = shutil.which("libreoffice") or shutil.which("soffice")
    if not lo_bin:
        raise ConvertError("libreoffice_missing")

    if action == "doc_to_pdf":
        proc = await asyncio.create_subprocess_exec(
            lo_bin, "--headless", "--convert-to", "pdf",
            "--outdir", str(tmp_dir), str(in_path),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        _, err = await proc.communicate()
        if proc.returncode != 0:
            raise ConvertError(f"libreoffice_failed:{err.decode()[:200]}")

        out = tmp_dir / f"{stem}.pdf"
        _check_out(out)
        return ConvertResult(out_path=out, tmp_dir=tmp_dir)

    if action == "doc_to_txt":
        proc = await asyncio.create_subprocess_exec(
            lo_bin, "--headless", "--convert-to", "txt:Text",
            "--outdir", str(tmp_dir), str(in_path),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        _, err = await proc.communicate()
        if proc.returncode != 0:
            raise ConvertError(f"libreoffice_failed:{err.decode()[:200]}")

        out = tmp_dir / f"{stem}.txt"
        _check_out(out)
        return ConvertResult(out_path=out, tmp_dir=tmp_dir)

    raise ConvertError(f"unknown_doc_action:{action}")


def _check_out(path: Path) -> None:
    if not path.exists() or path.stat().st_size == 0:
        raise ConvertError("output_empty")