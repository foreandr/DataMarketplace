from __future__ import annotations

from pathlib import Path


AGENCIES_PATH = Path(__file__).with_name("agencies.txt")


def iter_agencies(path: Path = AGENCIES_PATH) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> None:
    for agency in iter_agencies():
        print(agency)


if __name__ == "__main__":
    main()
