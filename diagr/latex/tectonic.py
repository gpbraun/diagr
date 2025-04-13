"""
Base de dados para problemas de química, Gabriel Braun, 2024

Esse módulo implementa funções do TECTONIC.
"""

__all__ = [
    "tectonic_compile",
]


import importlib.resources as resources
import re
import subprocess
import time
from collections import namedtuple
from pathlib import Path

from diagr.console import console
from diagr.utils import Error, Status

TEXINPUTS_ROOT = resources.files("diagr").joinpath("latex")
TEXINPUTS_PATHS = [
    folder
    for folder in TEXINPUTS_ROOT.glob("**/")
    if folder.is_dir() and folder.name != "__pycache__"
]

TECTONIC_ERROR_PATTERN = re.compile(
    r"(?P<type>warning|error): (?P<file>[^:]+):(?P<line>\d+): (?P<message>.+)"
)

HEDGEDOC_GRAPHICS_PATH = Path("/var/lib/docker/volumes/hedgedoc_uploads/_data/")


def parse_log(tex_path: Path, log_str: str) -> list[Error] | None:
    """
    Retorna: retorna erros no `.log` do TECTONIC.
    """
    if not log_str:
        return

    errors = []
    for match in TECTONIC_ERROR_PATTERN.finditer(log_str):
        error_type = match.group("type")
        file_path = tex_path.parent.joinpath("problems", match.group("file"))
        line_num = int(match.group("line"))
        message = match.group("message")

        if error_type != "error" or not file_path.exists():
            # ignora os warnings/erros de arquivos inexistentes (não deveriam acontecer)
            continue

        snippet = "\n".join(
            file_path.read_text().splitlines()[line_num - 3 : line_num + 2]
        )
        error = Error(file=file_path, line=line_num, message=message, snippet=snippet)
        errors.append(error)

    return errors


def tectonic_search_paths(search_paths: list[Path]) -> list[str]:
    """
    Retorna: diretórios para busca pelo TECTONIC.
    """
    search_paths.extend(TEXINPUTS_PATHS)

    # TODO: O DIRETÓRIO ESTÁ HARD-CODED!
    search_paths.append(HEDGEDOC_GRAPHICS_PATH)

    return [f"-Zsearch-path={str(search_path)}" for search_path in search_paths]


TectonicOutput = namedtuple("TectonicOutpt", ["status", "errors"])


def tectonic_compile(tex_path: Path, search_paths: list[Path] = None):
    """
    Retorna: lista de erros de compilação TECTONIC.
    """
    start_time = time.time()
    tectonic = subprocess.run(
        [
            "tectonic",
            "-X",
            "compile",
            "--keep-intermediates",
            "--keep-logs",
            "-Zcontinue-on-errors",
            *tectonic_search_paths(search_paths),
            str(tex_path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    runtime = time.time() - start_time
    if tectonic.stderr:
        err_path = tex_path.with_suffix(".tectonic.log")
        err_path.write_text(tectonic.stderr)
    pdf_path = tex_path.with_suffix(".pdf")

    errors = parse_log(tex_path, tectonic.stderr)
    status = Status.LATEX_ERROR if errors or not pdf_path.exists() else Status.LATEX_OK

    console.print(
        "Compilado em",
        f"[bold yellow]{runtime:.0f}s[/bold yellow].",
        "Status:",
        "[bold cyan]OK!" if status == Status.LATEX_OK else "[bold red]ERRO!",
        "\n",
    )

    return TectonicOutput(status, errors)
