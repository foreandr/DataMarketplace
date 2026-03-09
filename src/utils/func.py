import re
from pathlib import Path

def flatten_file(file_path: str):
    path = Path(file_path)
    if not path.exists():
        print(f"File {file_path} not found.")
        return

    # Read the content
    content = path.read_text(encoding='utf-8')

    # This regex looks for newlines and replaces them with a space
    # but you can also just use .replace('\n', ' ') if you want it all on one line
    cleaned_content = content.replace('\n', ' ')

    # Optional: If you want to keep the ['id', 'name'...] structure 
    # but just fix the internal breaks, we can fix the spacing:
    cleaned_content = re.sub(r'\s+', ' ', cleaned_content)

    # Write to a new file to be safe
    output_path = path.parent / f"cleaned_{path.name}"
    output_path.write_text(cleaned_content, encoding='utf-8')
    
    print(f"Done! Cleaned file saved to: {output_path}")

if __name__ == "__main__":
    # Put your path here
    target_path = r"../crawlers/logs/2026/03/09/2026-03-09.txt" 
    flatten_file(target_path)