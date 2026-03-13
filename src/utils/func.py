import re
from pathlib import Path

def print_tree(
    root: str | Path = None,
    max_depth: int | None = None,
    skip_folders: list[str] | None = None,
) -> None:
    base = Path(root) if root else Path(__file__).resolve().parents[2]
    if not base.exists():
        print(f"Root {base} not found.")
        return

    skips = {s.lower() for s in (skip_folders or [])}

    def _walk(path: Path, prefix: str = "", depth: int = 0) -> None:
        if max_depth is not None and depth > max_depth:
            return

        try:
            entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        except Exception:
            return

        filtered = [e for e in entries if e.name.lower() not in skips]
        for i, entry in enumerate(filtered):
            is_last = i == len(filtered) - 1
            branch = "└── " if is_last else "├── "
            print(f"{prefix}{branch}{entry.name}")
            if entry.is_dir():
                extension = "    " if is_last else "│   "
                _walk(entry, prefix + extension, depth + 1)

    print(base.name)
    _walk(base)

def flatten_file(file_path: str):
    path = Path(file_path)
    if not path.exists():
        print(f"File {file_path} not found.")
        return

    content = path.read_text(encoding='utf-8')

    # 1. Fix the internal strings: 'string'\n'string' -> 'string', 'string'
    # We look for a quote, a newline (plus potential whitespace), and another quote
    content = re.sub(r"'\s*\n\s*'", "', '", content)

    # 2. Fix the list boundaries: ]\n[ -> ], [
    content = re.sub(r"\]\s*\n\s*\[", "], [", content)

    # 3. Clean up any remaining internal newlines (like in 'East Brunswick\nNJ')
    # We replace newlines that are inside quotes with a space
    content = content.replace('\n', ' ')

    # 4. Collapse extra whitespace
    content = re.sub(r'\s+', ' ', content)

    output_path = path.parent / f"fixed_{path.name}"
    output_path.write_text(content, encoding='utf-8')
    
    print(f"Done! Valid Python data saved to: {output_path}")

if __name__ == "__main__":
    # Put your path here
    #target_path = r"../crawlers/logs/2026/03/09/2026-03-09.txt" 
    #flatten_file(target_path)

    # Print tree (skip noisy folders by default)
    SKIP_FOLDERS = ["logs", "report", "demo_data", "__pycache__", ".git", "venv"]
    print_tree(skip_folders=SKIP_FOLDERS)
