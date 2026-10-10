#!/usr/bin/env python3
"""
LaTeX to PDF Compiler via Docker (blang/latex:latest)

Compiles LaTeX documents (.tex) into publication-ready PDFs using a containerized
pdflatex environment. Performs two compilation passes to accurately resolve
tables of contents, cross-references, and auxiliary artifacts.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional


DEFAULT_DOCKER_IMAGE = "blang/latex:latest"


def find_workspace_root(start_path: Path) -> Path:
    """
    Find the closest repository root containing .git, pyproject.toml, or package.json.
    Defaults to parent directory if no marker is found.
    """
    current = start_path.resolve()
    for parent in [current] + list(current.parents):
        if (parent / ".git").exists() or (parent / ".gitmodules").exists() or (parent / "pyproject.toml").exists():
            return parent
    return start_path.parent.resolve()


def compile_tex_file(
    tex_path: Path,
    docker_image: str = DEFAULT_DOCKER_IMAGE,
    clean_aux: bool = False,
    verbose: bool = False,
) -> bool:
    """
    Compile a single .tex file into .pdf using Docker.

    Parameters
    ----------
    tex_path : Path
        Absolute or relative path to the .tex file.
    docker_image : str, default="blang/latex:latest"
        Docker image tag containing pdflatex.
    clean_aux : bool, default=False
        Whether to delete auxiliary files (.aux, .log, .out, .toc) after compilation.
    verbose : bool, default=False
        Whether to print full pdflatex stdout.

    Returns
    -------
    bool
        True if PDF was successfully produced, False otherwise.
    """
    resolved_path = tex_path.resolve()
    if not resolved_path.exists():
        print(f"❌ Error: File not found: {resolved_path}", file=sys.stderr)
        return False

    if resolved_path.suffix != ".tex":
        print(f"❌ Error: Expected a .tex file, got: {resolved_path.name}", file=sys.stderr)
        return False

    target_dir = resolved_path.parent
    tex_filename = resolved_path.name
    pdf_filename = resolved_path.stem + ".pdf"
    expected_pdf = target_dir / pdf_filename

    # Determine workspace root for volume mount
    workspace_root = find_workspace_root(target_dir)

    try:
        rel_working_dir = target_dir.relative_to(workspace_root)
        container_workdir = f"/workdir/{rel_working_dir.as_posix()}"
    except ValueError:
        workspace_root = target_dir
        container_workdir = "/workdir"

    print(f"\n📄 Compiling LaTeX: {resolved_path.relative_to(workspace_root) if workspace_root in resolved_path.parents else resolved_path}")
    print(f"   🐳 Docker Image: {docker_image}")
    print(f"   📂 Mount Point: {workspace_root} -> /workdir")
    print(f"   📍 Container Workdir: {container_workdir}")

    # Two-pass pdflatex command: Pass 1 builds aux/toc/citations, Pass 2 resolves references
    docker_cmd: List[str] = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{workspace_root}:/workdir",
        "-w",
        container_workdir,
        docker_image,
        "bash",
        "-c",
        (
            f"pdflatex -interaction=nonstopmode {tex_filename} && "
            f"pdflatex -interaction=nonstopmode {tex_filename}"
        ),
    ]

    try:
        result = subprocess.run(
            docker_cmd,
            capture_output=True,
            text=True,
            check=False,
        )

        if verbose:
            print("\n--- pdflatex Output ---")
            print(result.stdout)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            print("-----------------------\n")

        if expected_pdf.exists() and expected_pdf.stat().st_size > 0:
            print(f"✅ PDF compiled successfully: {expected_pdf} ({expected_pdf.stat().st_size} bytes)")

            if clean_aux:
                aux_extensions = [".aux", ".log", ".out", ".toc", ".nav", ".snm", ".vrb", ".fls", ".fdb_latexmk"]
                cleaned = []
                for ext in aux_extensions:
                    aux_file = target_dir / (resolved_path.stem + ext)
                    if aux_file.exists():
                        aux_file.unlink()
                        cleaned.append(ext)
                if cleaned:
                    print(f"🧹 Cleaned auxiliary files: {', '.join(cleaned)}")

            return True
        else:
            print(f"❌ PDF generation failed for {tex_filename}. Exit code: {result.returncode}", file=sys.stderr)
            if not verbose:
                # Print trailing lines of stdout for error diagnosis
                stdout_lines = result.stdout.splitlines()[-25:]
                print("\nLast 25 lines of compiler output:", file=sys.stderr)
                print("\n".join(stdout_lines), file=sys.stderr)
            return False

    except FileNotFoundError:
        print("❌ Error: Docker executable not found in system PATH. Ensure Docker daemon is installed and running.", file=sys.stderr)
        return False
    except Exception as e:
        print(f"❌ Unexpected compilation error: {e}", file=sys.stderr)
        return False


def discover_tex_files(search_dir: Path) -> List[Path]:
    """Recursively discover all .tex files in a directory."""
    return sorted([p for p in search_dir.rglob("*.tex") if not p.name.startswith(".")])


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compile LaTeX (.tex) files to PDF using Docker (blang/latex:latest)."
    )
    parser.add_argument(
        "targets",
        nargs="*",
        type=str,
        help="Path(s) to .tex file(s) or directory to compile.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Discover and compile all .tex files across the repository.",
    )
    parser.add_argument(
        "--dir",
        type=str,
        help="Search and compile all .tex files in the specified directory.",
    )
    parser.add_argument(
        "--image",
        type=str,
        default=DEFAULT_DOCKER_IMAGE,
        help=f"Docker LaTeX image (default: {DEFAULT_DOCKER_IMAGE}).",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean up auxiliary files (.aux, .log, .out, .toc) after successful compilation.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Display full compiler stdout and stderr.",
    )

    args = parser.parse_args()

    files_to_compile: List[Path] = []

    if args.all:
        repo_root = find_workspace_root(Path.cwd())
        files_to_compile.extend(discover_tex_files(repo_root))
    elif args.dir:
        target_directory = Path(args.dir).resolve()
        if not target_directory.is_dir():
            print(f"❌ Error: Not a valid directory: {target_directory}", file=sys.stderr)
            return 1
        files_to_compile.extend(discover_tex_files(target_directory))
    elif args.targets:
        for t in args.targets:
            p = Path(t).resolve()
            if p.is_dir():
                files_to_compile.extend(discover_tex_files(p))
            elif p.is_file() and p.suffix == ".tex":
                files_to_compile.append(p)
            else:
                print(f"⚠️ Warning: Skipping invalid target: {t}", file=sys.stderr)
    else:
        # Default: compile math.tex in the current working directory if present
        local_tex = Path.cwd() / "math.tex"
        if local_tex.exists():
            files_to_compile.append(local_tex)
        else:
            parser.print_help()
            return 1

    if not files_to_compile:
        print("⚠️ No .tex files found to compile.")
        return 0

    print(f"📋 Found {len(files_to_compile)} LaTeX file(s) to compile.")

    success_count = 0
    failure_count = 0

    for tex_file in files_to_compile:
        success = compile_tex_file(
            tex_path=tex_file,
            docker_image=args.image,
            clean_aux=args.clean,
            verbose=args.verbose,
        )
        if success:
            success_count += 1
        else:
            failure_count += 1

    print(f"\n========================================")
    print(f"📊 Summary: {success_count} succeeded, {failure_count} failed out of {len(files_to_compile)} total.")
    print(f"========================================")

    return 0 if failure_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
