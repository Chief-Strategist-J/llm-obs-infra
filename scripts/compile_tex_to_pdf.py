#!/usr/bin/env python3
"""
LaTeX to PDF Bulk Compiler & Auxiliary File Cleaner via Docker (blang/latex:latest)

Compiles LaTeX documents (.tex) into publication-ready PDFs using a containerized
pdflatex environment with automatic two-pass reference resolution and automated
auxiliary file (.aux, .log, .out, .toc, etc.) cleanup.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Set

DEFAULT_DOCKER_IMAGE = "blang/latex:latest"
AUX_EXTENSIONS: Set[str] = {
    ".aux",
    ".log",
    ".out",
    ".toc",
    ".nav",
    ".snm",
    ".vrb",
    ".fls",
    ".fdb_latexmk",
    ".synctex.gz",
}


def find_workspace_root(start_path: Path) -> Path:
    current = start_path.resolve()
    for parent in [current] + list(current.parents):
        if (parent / ".git").exists() or (parent / ".gitmodules").exists() or (parent / "pyproject.toml").exists():
            return parent
    return start_path.parent.resolve()


def clean_auxiliary_files(directory: Path, stem: Optional[str] = None) -> List[Path]:
    deleted: List[Path] = []
    if not directory.exists() or not directory.is_dir():
        return deleted

    for item in directory.iterdir():
        if item.is_file() and item.suffix.lower() in AUX_EXTENSIONS:
            if stem is None or item.stem == stem:
                try:
                    item.unlink()
                    deleted.append(item)
                except OSError as e:
                    print(f"⚠️ Warning: Could not delete {item}: {e}", file=sys.stderr)

    return deleted


def discover_tex_files(search_dir: Path) -> List[Path]:
    return sorted([p for p in search_dir.rglob("*.tex") if not p.name.startswith(".")])


def compile_tex_files_bulk(
    tex_files: List[Path],
    docker_image: str = DEFAULT_DOCKER_IMAGE,
    clean_aux: bool = True,
    verbose: bool = False,
) -> int:
    if not tex_files:
        print("⚠️ No .tex files provided for compilation.")
        return 0

    workspace_root = find_workspace_root(Path.cwd())
    print(f"\n========================================================")
    print(f"🚀 LaTeX Bulk Compiler: {len(tex_files)} file(s) found")
    print(f"🐳 Docker Image: {docker_image}")
    print(f"📂 Mount Point: {workspace_root} -> /workdir")
    print(f"🧹 Auto-Clean Auxiliary Files: {clean_aux}")
    print(f"========================================================\n")

    if clean_aux:
        for tex_path in tex_files:
            clean_auxiliary_files(tex_path.parent, tex_path.stem)

    success_count = 0
    failure_count = 0

    commands: List[str] = []
    for tex_path in tex_files:
        resolved = tex_path.resolve()
        target_dir = resolved.parent
        try:
            rel_dir = target_dir.relative_to(workspace_root).as_posix()
            container_dir = f"/workdir/{rel_dir}"
        except ValueError:
            container_dir = "/workdir"

        tex_name = resolved.name
        pdf_name = resolved.stem + ".pdf"

        cmd = (
            f"cd {container_dir} && "
            f"echo '📄 Compiling {tex_name}...' && "
            f"pdflatex -interaction=nonstopmode {tex_name} > /dev/null 2>&1 && "
            f"pdflatex -interaction=nonstopmode {tex_name} > /dev/null 2>&1 && "
            f"echo '✅ Done: {pdf_name}'"
        )
        commands.append(cmd)

    full_bash_script = "; ".join(commands)

    docker_cmd = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{workspace_root}:/workdir",
        docker_image,
        "bash",
        "-c",
        full_bash_script,
    ]

    try:
        proc = subprocess.run(
            docker_cmd,
            capture_output=not verbose,
            text=True,
            check=False,
        )

        if verbose and proc.stdout:
            print(proc.stdout)
        if verbose and proc.stderr:
            print(proc.stderr, file=sys.stderr)

    except FileNotFoundError:
        print("❌ Error: Docker executable not found. Ensure Docker is installed and running.", file=sys.stderr)
        return len(tex_files)
    except Exception as e:
        print(f"❌ Error during Docker execution: {e}", file=sys.stderr)

    for tex_path in tex_files:
        resolved = tex_path.resolve()
        pdf_path = resolved.parent / (resolved.stem + ".pdf")
        if pdf_path.exists() and pdf_path.stat().st_size > 0:
            print(f"✅ Successfully compiled: {pdf_path.relative_to(workspace_root) if workspace_root in pdf_path.parents else pdf_path} ({pdf_path.stat().st_size} bytes)")
            success_count += 1
        else:
            print(f"❌ Failed to produce PDF: {pdf_path.name}", file=sys.stderr)
            failure_count += 1

        if clean_aux:
            cleaned = clean_auxiliary_files(resolved.parent, resolved.stem)
            if cleaned:
                print(f"   🧹 Removed {len(cleaned)} auxiliary files (.aux, .log, .out, etc.)")

    print(f"\n========================================================")
    print(f"📊 Summary: {success_count} succeeded, {failure_count} failed out of {len(tex_files)} total.")
    print(f"========================================================\n")

    return failure_count


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compile LaTeX (.tex) files to publication-ready PDFs in bulk and clean auxiliary files."
    )
    parser.add_argument(
        "targets",
        nargs="*",
        type=str,
        help="Path(s) to .tex file(s) or directories to compile.",
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
        "--clean-only",
        action="store_true",
        help="Only delete auxiliary files (.aux, .log, .out, .toc, etc.) without compiling.",
    )
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="Keep auxiliary files after compilation (disabled by default).",
    )
    parser.add_argument(
        "--image",
        type=str,
        default=DEFAULT_DOCKER_IMAGE,
        help=f"Docker LaTeX image (default: {DEFAULT_DOCKER_IMAGE}).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Display full compiler stdout and stderr.",
    )

    args = parser.parse_args()
    repo_root = find_workspace_root(Path.cwd())

    files_to_compile: List[Path] = []

    if args.all or (not args.targets and not args.dir):
        files_to_compile.extend(discover_tex_files(repo_root))
    elif args.dir:
        target_dir = Path(args.dir).resolve()
        if not target_dir.is_dir():
            print(f"❌ Error: Invalid directory: {target_dir}", file=sys.stderr)
            return 1
        files_to_compile.extend(discover_tex_files(target_dir))
    elif args.targets:
        for t in args.targets:
            p = Path(t).resolve()
            if p.is_dir():
                files_to_compile.extend(discover_tex_files(p))
            elif p.is_file() and p.suffix == ".tex":
                files_to_compile.append(p)
            else:
                print(f"⚠️ Warning: Skipping invalid target: {t}", file=sys.stderr)

    if not files_to_compile:
        print("⚠️ No .tex files found.")
        return 0

    if args.clean_only:
        total_cleaned = 0
        for tex_file in files_to_compile:
            cleaned = clean_auxiliary_files(tex_file.parent, tex_file.stem)
            total_cleaned += len(cleaned)
        print(f"🧹 Clean-only complete: Removed {total_cleaned} auxiliary file(s).")
        return 0

    clean_aux = not args.no_clean
    failures = compile_tex_files_bulk(
        tex_files=files_to_compile,
        docker_image=args.image,
        clean_aux=clean_aux,
        verbose=args.verbose,
    )

    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
