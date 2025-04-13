import argparse
import configparser
import importlib.resources as resources
from pathlib import Path

import psycopg2
from pydantic import ValidationError

from diagr import VERSION, Exam
from diagr.console import console
from diagr.utils import Status

DEFAULT_CONFIG_PATH = resources.files("diagr.bin").joinpath("defaults.cfg")


def get_json_path(arg_path: Path):
    """
    Retorna: endereço do arquivo `.json`.
    """
    path = Path(arg_path)

    if path.suffix == ".json":
        if not path.exists():
            return

    if path.is_dir():
        json_files = list(arg_path.glob("*.json"))
        if not json_files:
            return
        path = json_files[0]

    return path


def read_config(config_path: Path):
    """
    Retorna: configurações do diagramador.
    """
    config = configparser.ConfigParser()
    config.read(DEFAULT_CONFIG_PATH)

    if config_path and config_path.exists():
        config.read(config_path)
        console.print(
            "Arquivo de configuração:",
            f"[magenta]'{config_path}'\n",
        )

    return config


def main():
    """
    Diagr.
    """
    parser = argparse.ArgumentParser(
        prog="Diagramador",
        description="Cria arquivos .pdf de avaliações a partir de arquivos markdown.",
        epilog="Gabriel Braun, 2025",
    )

    # MOSTRA A VERSÃO DO DIAGRAMADOR.
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"DIAGR versão {VERSION}",
    )

    parser.add_argument(
        "path",
        type=Path,
        help="endereço do arquivo da avaliação JSON.",
    )
    parser.add_argument(
        "-c",
        "--config-file",
        type=Path,
        help="endereço do arquivo de configuração.",
    )
    parser.add_argument(
        "-l",
        "--local",
        action="store_true",
        default=False,
        help="diagramação de arquivos locais.",
    )
    parser.add_argument(
        "-e",
        "--pdf-exam",
        action="store_true",
        default=False,
        help="gera o .pdf da avaliação.",
    )
    parser.add_argument(
        "-s",
        "--pdf-solution",
        action="store_true",
        default=False,
        help="gera o .pdf do gabarito.",
    )

    args = parser.parse_args()

    console.rule("[bold blue]Diagramador")

    config = read_config(args.config_file)

    # procura o arquivo de configurações `.json`
    path = get_json_path(args.path)
    if not path:
        console.print(
            "[bold red]ERRO!",
            "Arquivo '.json' não encontrado em:",
            f"[magenta]'{args.path}'",
        )
        console.rule()
        return

    # valida o `.json`
    try:
        exam = Exam.parse_jsonfile(path)
    except ValidationError as exc:
        console.print("[bold red]ERRO!", exc)
        console.rule()
        return

    # modo hedgedoc/local
    if not exam.local:
        exam.local = args.local

    # modo local/hedgedoc
    if not args.local:
        try:
            # parâmetros do arquivo de configuração para conexão
            host = config["hedgedoc"]["host"]
            port = config["hedgedoc"]["port"]
            database = config["hedgedoc"]["database"]
            user = config["hedgedoc"]["user"]
            password = config["hedgedoc"]["password"]
            # conexão pelo psycopg2
            conn = psycopg2.connect(
                host=host, port=port, database=database, user=user, password=password
            )
            cursor = conn.cursor()
            console.print(
                "[bold cyan]CONECTADO!",
                "Carregando problemas da base de dados",
                f"[green]{database}",
                "em",
                f"[green]{host}:{port}",
                "\n",
            )
        except Exception as exc:
            console.print("[bold red]ERRO!", exc)
            exam.status = Status.DATABASE_ERROR
    else:
        cursor = None
        console.print(
            "Carregando problemas no diretório local",
            f"[magenta]'{exam.path.parent}'\n",
        )

    # carrega os problemas.
    if exam.status_ok():
        exam.process_problems(cursor)

    # executa os comandos para criação do `.pdf`
    if args.pdf_exam and exam.status_ok():
        exam.create_exam_pdf()
    if args.pdf_solution and exam.status_ok():
        exam.create_solution_pdf()

    # escreve o arquivo `.json`` da avaliação
    json_path = exam.tmp_path.joinpath("_status").with_suffix(".json")
    json_path.write_text(exam.model_dump_json(indent=4))

    console.print(
        "Diagramação [bold]finalizada[/bold]. Status:",
        "[bold cyan]OK!" if exam.status_ok() else "[bold red]ERRO!",
    )
    console.rule()


if __name__ == "__main__":
    main()
