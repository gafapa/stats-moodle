import os
import tempfile
import unittest

from src.pdf_export import export_text_pdf


class PdfExportTests(unittest.TestCase):
    def test_export_text_pdf_writes_valid_pdf_header(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "informe.pdf")

            export_text_pdf(path, "Informe de prueba", "Linea 1\nLinea 2")

            self.assertTrue(os.path.exists(path))
            with open(path, "rb") as f:
                content = f.read()
            self.assertTrue(content.startswith(b"%PDF-1.4"))
            self.assertIn(b"%%EOF", content)

    def test_export_markdown_removes_markdown_markers_from_pdf(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "informe-md.pdf")

            export_text_pdf(path, "Informe", "# Titulo\n\n- Punto\n\n**Negrita**")

            with open(path, "rb") as f:
                content = f.read()
            self.assertNotIn(b"**", content)
            self.assertNotIn(b"# Titulo", content)


if __name__ == "__main__":
    unittest.main()
