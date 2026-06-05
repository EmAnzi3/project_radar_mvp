import html
import os
import re
from urllib.parse import urljoin
from urllib.request import Request, urlopen


PAGE_URL = (
    "https://www.opencup.gov.it/portale/web/opencup/"
    "dettaglio-opendata-complessivo"
)

LINK_RE = re.compile(
    r'''href=["']([^"']*OpendataComplessivo\.zip[^"']*)["']''',
    flags=re.IGNORECASE,
)


def write_github_output(name: str, value: str) -> None:
    output_path = os.getenv("GITHUB_OUTPUT", "").strip()

    if not output_path:
        return

    with open(output_path, "a", encoding="utf-8") as f:
        f.write(f"{name}={value}\n")


def main() -> int:
    override = os.getenv("OPENCUP_URL_OVERRIDE", "").strip()

    if override:
        url = override
        source = "override manuale"
    else:
        request = Request(
            PAGE_URL,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 ProjectRadar/1.0 "
                    "(GitHub Actions OpenCUP updater)"
                )
            },
        )

        with urlopen(request, timeout=120) as response:
            body = response.read().decode("utf-8", errors="ignore")

        matches = LINK_RE.findall(body)

        if not matches:
            raise SystemExit(
                "ERRORE: link OpendataComplessivo.zip non trovato "
                "nella pagina OpenCUP."
            )

        url = urljoin(PAGE_URL, html.unescape(matches[0]))
        source = PAGE_URL

    if not url.lower().startswith(("https://", "http://")):
        raise SystemExit(f"ERRORE: URL OpenCUP non valido: {url}")

    print(f"[OpenCUP] Fonte URL: {source}")
    print(f"[OpenCUP] ZIP risolto: {url}")

    write_github_output("url", url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
