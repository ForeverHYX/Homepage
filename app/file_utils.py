from __future__ import annotations
from pathlib import Path
from PIL import Image
from fastapi import HTTPException

def process_uploaded_image(file_path: Path) -> str:
    """Converts JPG to WebP and returns the new filename."""
    if file_path.suffix.lower() in ['.jpg', '.jpeg']:
        try:
            with Image.open(file_path) as img:
                # Convert to RGB if needed
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize if too huge (optional, but good for galleries)
                if max(img.size) > 1920:
                    img.thumbnail((1920, 1920))

                webp_path = file_path.with_suffix('.webp')
                img.save(webp_path, 'WEBP', quality=80)
            
            # Remove original
            file_path.unlink()
            return webp_path.name
        except Exception as e:
            print(f"Error converting image {file_path}: {e}")
    return file_path.name

def safe_join(base: Path, target: str) -> Path:
    """Join base and target, ensuring the result stays under base."""
    base = base.resolve()
    candidate = (base / target).resolve()
    try:
        candidate.relative_to(base)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid path")
    return candidate
