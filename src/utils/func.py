import re
from pathlib import Path

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
    target_path = r"../crawlers/logs/2026/03/09/2026-03-09.txt" 
    flatten_file(target_path)