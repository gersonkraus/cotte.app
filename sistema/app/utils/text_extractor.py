import pdfplumber
import io

def extract_text_from_pdf(content: bytes) -> str:
    """Extrai texto de um arquivo PDF usando pdfplumber."""
    text = ""
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"Erro ao extrair PDF: {e}")
    return text

def extract_text_from_txt(content: bytes) -> str:
    """Extrai texto de um arquivo TXT decodificando como UTF-8."""
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return content.decode("latin-1", errors="ignore")
