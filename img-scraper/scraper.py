#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Image Web Scraper configurable.

- Lee un JSON de configuración con:
  - startPage (str)
  - headers (dict, opcional)
  - action: { tag: str, filters: [{prop, value}], action: {type: "click"} }
  - imageFilter: { types: list[str], minKB: int }
  - output: { directory: str, naming: str }   <-- soporta Name_{index}.{ext}
  - limit: int
  - request: { timeoutSeconds: int, delaySeconds: float }
- Descarga imágenes de <img src> filtradas por extensión y tamaño mínimo.
- Navega siguiendo el href de la acción configurada (paginación clásica).
- Evita loops con sets de visitados.

CLI:
  python scraper.py --config config.json --output ./output --verbose
  # Si --output no se pasa, se usa config.output.directory (si existe)
  # El nombre de archivo puede venir de config.output.naming:
  #   - {index}     -> índice (con zero-padding automático según limit; p.ej. 0001 si limit=1000)
  #   - {ext}       -> extensión en minúsculas (sin punto)
  #   - También puedes usar formato Python explícito: {index:05d} (si lo usas, se respeta tal cual)
"""

from __future__ import annotations
import argparse
import json
import logging
import re
import time
from dataclasses import dataclass, field
from hashlib import sha1
from pathlib import Path
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field, ValidationError, field_validator
from tqdm import tqdm


# ==============================
# Config models
# ==============================

class FilterModel(BaseModel):
    """Filtro por atributo HTML (coincidencia exacta)."""
    prop: str
    value: str


class ActionInnerModel(BaseModel):
    type: str = Field(..., pattern=r"^(click)$")


class ActionModel(BaseModel):
    tag: str
    filters: List[FilterModel] = Field(default_factory=list)
    action: ActionInnerModel


class ImageFilterModel(BaseModel):
    types: List[str]
    minKB: int = Field(ge=0)

    @field_validator("types")
    @classmethod
    def normalize_exts(cls, v: List[str]) -> List[str]:
        return [ext.lower().lstrip(".") for ext in v]


class RequestModel(BaseModel):
    timeoutSeconds: int = Field(default=20, ge=1, le=120)
    delaySeconds: float = Field(default=1.0, ge=0.0, le=10.0)


class OutputModel(BaseModel):
    directory: str
    naming: str = Field(default="Name_{index}.{ext}")  # soporta {index} y {ext}


class ConfigModel(BaseModel):
    startPage: str
    headers: Dict[str, str] = Field(default_factory=dict)
    action: ActionModel
    imageFilter: ImageFilterModel
    output: Optional[OutputModel] = None
    limit: int = Field(default=100, ge=1, le=10000)
    request: RequestModel = Field(default_factory=RequestModel)


# ==============================
# Core scraper
# ==============================

@dataclass
class ScraperContext:
    session: requests.Session
    output_dir: Path
    visited_pages: Set[str] = field(default_factory=set)
    visited_images: Set[str] = field(default_factory=set)
    actions_done: int = 0
    image_index: int = 1


class ImageScraper:
    """
    Implementa el ciclo:
    1) GET página actual
    2) Descargar imágenes filtradas
    3) Buscar acción (siguiente URL) y saltar
    4) Repetir hasta 'limit' o no encontrar acción
    """

    def __init__(self, config: ConfigModel, output_dir: Path):
        self.cfg = config
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.ctx = ScraperContext(session=requests.Session(), output_dir=output_dir)
        # Configura headers si llegan
        if self.cfg.headers:
            self.ctx.session.headers.update(self.cfg.headers)

        # Ancho de zero-padding basado en limit (p.ej. limit=1000 -> width=4 -> 0001)
        self.pad_width = max(1, len(str(self.cfg.limit)))

    # ---------- utils ----------
    @staticmethod
    def _is_allowed_image(url: str, allowed_exts: List[str]) -> bool:
        path = urlparse(url).path.lower()
        m = re.search(r"\.([a-z0-9]+)$", path)
        if not m:
            return False
        return m.group(1) in allowed_exts

    @staticmethod
    def _extract_ext(url: str, default: str = "jpg") -> str:
        path = urlparse(url).path.lower()
        m = re.search(r"\.([a-z0-9]+)$", path)
        return m.group(1) if m else default

    @staticmethod
    def _safe_hash_name(url: str) -> str:
        # hash para evitar nombres repetidos / inválidos
        h = sha1(url.encode("utf-8")).hexdigest()[:12]
        name = urlparse(url).path.split("/")[-1] or "image"
        return f"{h}_{name}"

    def _format_index(self, index: int) -> str:
        """Devuelve el índice con zero-padding según pad_width (derivado de limit)."""
        return f"{index:0{self.pad_width}d}"

    def _make_filename(self, img_url: str, index: int) -> str:
        ext = self._extract_ext(img_url)
        naming = None
        if self.cfg.output and self.cfg.output.naming:
            naming = self.cfg.output.naming

        if naming:
            # Si el usuario ya especificó formato explícito (ej. {index:05d}), respetarlo
            if "{index:" in naming:
                try:
                    return naming.format(index=index, ext=ext)
                except Exception as e:
                    logging.warning("Naming con formato explícito inválido '%s': %s. Usando hash.", naming, e)
            else:
                # Aplicar zero-padding automático usando limit
                idx_str = self._format_index(index)
                candidate = naming.replace("{index}", idx_str).replace("{ext}", ext)
                # Si aún quedan placeholders sin resolver, haz fallback
                if "{" in candidate or "}" in candidate:
                    logging.warning("Naming contiene placeholders no soportados: '%s'. Usando hash.", naming)
                else:
                    return candidate

        # Fallback seguro
        return self._safe_hash_name(img_url)

    def _download_image(self, img_url: str, min_kb: int) -> Optional[Path]:
        if img_url in self.ctx.visited_images:
            logging.debug("Imagen repetida, saltando: %s", img_url)
            return None

        try:
            resp = self.ctx.session.get(img_url, stream=True, timeout=self.cfg.request.timeoutSeconds)
        except requests.RequestException as e:
            logging.warning("Fallo al descargar imagen %s: %s", img_url, e)
            return None

        if resp.status_code != 200:
            logging.debug("Status %s al bajar imagen %s", resp.status_code, img_url)
            return None

        min_bytes = min_kb * 1024
        content_len = resp.headers.get("Content-Length")
        if content_len is not None:
            try:
                if int(content_len) < min_bytes:
                    logging.debug("Imagen < minKB por Content-Length: %s", img_url)
                    return None
            except ValueError:
                pass

        fname = self._make_filename(img_url, self.ctx.image_index)
        fpath = self.output_dir / fname

        total = 0
        try:
            with open(fpath, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if not chunk:
                        continue
                    f.write(chunk)
                    total += len(chunk)
        finally:
            resp.close()

        if total < min_bytes:
            logging.debug("Imagen < minKB por bytes medidos: %s", img_url)
            try:
                fpath.unlink(missing_ok=True)
            except Exception:
                pass
            return None

        # Solo incrementa índice si realmente guardamos
        self.ctx.visited_images.add(img_url)
        self.ctx.image_index += 1
        logging.info("Descargada: %s (%d KB)", fpath.name, total // 1024)
        return fpath

    def _extract_images(self, base_url: str, soup: BeautifulSoup) -> List[str]:
        urls: List[str] = []
        for img in soup.find_all("img"):
            src = img.get("src")
            if not src:
                continue
            abs_url = urljoin(base_url, src)
            urls.append(abs_url)
        return urls

    def _match_filters(self, el, filters: List[FilterModel]) -> bool:
        for flt in filters:
            attr_val = el.get(flt.prop)
            if attr_val is None:
                return False
            # class puede ser lista
            if isinstance(attr_val, list):
                if flt.value not in attr_val:
                    return False
            else:
                if str(attr_val) != flt.value:
                    return False
        return True

    def _find_next_url(self, base_url: str, soup: BeautifulSoup) -> Optional[str]:
        tag = self.cfg.action.tag
        filters = self.cfg.action.filters

        # Primero, busca el tag solicitado con filtros exactos
        candidates = soup.find_all(tag)
        for el in candidates:
            if not self._match_filters(el, filters):
                continue
            # Si es <a>, usa href
            if el.name == "a":
                href = el.get("href")
                if href:
                    return urljoin(base_url, href)
            # Si no es <a>, busca un <a> descendiente
            a = el.find("a", href=True)
            if a and a.get("href"):
                return urljoin(base_url, a.get("href"))

        # Heurística adicional: rel="next"
        link_next = soup.find("link", rel=lambda v: v and "next" in v)
        if link_next and link_next.get("href"):
            return urljoin(base_url, link_next.get("href"))

        a_next = soup.find("a", rel=lambda v: v and "next" in v, href=True)
        if a_next and a_next.get("href"):
            return urljoin(base_url, a_next.get("href"))

        return None

    def run(self) -> None:
        current_url = self.cfg.startPage
        delay = self.cfg.request.delaySeconds
        limit = self.cfg.limit

        pbar = tqdm(total=limit, desc="Acciones", unit="jump")

        try:
            while True:
                if current_url in self.ctx.visited_pages:
                    logging.warning("Página ya visitada, rompiendo para evitar loop: %s", current_url)
                    break
                self.ctx.visited_pages.add(current_url)

                logging.info("GET %s", current_url)
                try:
                    r = self.ctx.session.get(current_url, timeout=self.cfg.request.timeoutSeconds)
                    r.raise_for_status()
                except requests.RequestException as e:
                    logging.error("Error obteniendo %s: %s", current_url, e)
                    break

                soup = BeautifulSoup(r.text, "lxml")

                # Paso 2: imágenes
                imgs = self._extract_images(current_url, soup)
                allowed_exts = self.cfg.imageFilter.types
                min_kb = self.cfg.imageFilter.minKB

                for img_url in imgs:
                    if not self._is_allowed_image(img_url, allowed_exts):
                        continue
                    self._download_image(img_url, min_kb)

                # Paso 3: acción
                if self.ctx.actions_done >= limit:
                    logging.info("Límite de acciones alcanzado (%d).", limit)
                    break

                next_url = self._find_next_url(current_url, soup)
                if not next_url:
                    logging.info("No se encontró acción/navegación siguiente. Fin.")
                    break

                # Siguiente
                self.ctx.actions_done += 1
                pbar.update(1)
                logging.info("Siguiente (%d/%d): %s", self.ctx.actions_done, limit, next_url)

                # Delay de cortesía
                if delay > 0:
                    time.sleep(delay)

                current_url = next_url
        finally:
            pbar.close()


# ==============================
# CLI
# ==============================

def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Configurable Image Web Scraper")
    ap.add_argument("--config", required=True, help="Ruta a config.json")
    ap.add_argument("--output", required=False, help="Carpeta para imágenes (override de config.output.directory)")
    ap.add_argument("--limit", type=int, default=None, help="Sobrescribe config.limit")
    ap.add_argument("--delay", type=float, default=None, help="Sobrescribe request.delaySeconds")
    ap.add_argument("--verbose", action="store_true", help="Habilita logging INFO")
    return ap.parse_args()


def load_config(path: Path) -> ConfigModel:
    data = json.loads(path.read_text(encoding="utf-8"))
    try:
        cfg = ConfigModel(**data)
    except ValidationError as ve:
        raise SystemExit(f"Config inválida:\n{ve}") from ve
    return cfg


def main():
    args = parse_args()

    log_level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")

    cfg_path = Path(args.config)
    cfg = load_config(cfg_path)

    # Overrides
    if args.limit is not None:
        cfg.limit = args.limit
    if args.delay is not None:
        cfg.request.delaySeconds = args.delay

    # Resolve output directory: CLI overrides config, else error
    if args.output:
        out_dir = Path(args.output)
    elif cfg.output and cfg.output.directory:
        out_dir = Path(cfg.output.directory)
    else:
        raise SystemExit("Debe especificar --output o config.output.directory")

    scraper = ImageScraper(cfg, out_dir)
    scraper.run()


if __name__ == "__main__":
    main()
