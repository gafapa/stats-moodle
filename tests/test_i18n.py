import unittest

from src import i18n
from src.report_formatting import semantic_section_key


class I18nTests(unittest.TestCase):
    def test_translate_text_translates_fixed_labels(self):
        self.assertEqual(i18n.translate_text("Configuración de conexión", "en"), "Connection settings")
        self.assertEqual(i18n.translate_text("Resumen", "fr"), "Resume")
        self.assertEqual(i18n.translate_text("Email", "de"), "E-Mail")

    def test_translate_text_translates_dynamic_risk_messages(self):
        self.assertEqual(i18n.translate_text("Sin acceso desde hace 12 días", "en"), "No access for 12 days")
        self.assertEqual(i18n.translate_text("Solo ha entregado el 40% de las tareas", "ca"), "Nomes ha lliurat el 40% de les tasques")
        self.assertEqual(
            i18n.translate_text("Cobertura baja de cuestionarios: 25%", "en"),
            "Low quiz coverage: 25%",
        )
        self.assertEqual(
            i18n.translate_text("Obteniendo información del curso...", "en"),
            "Fetching course information...",
        )
        self.assertEqual(
            i18n.translate_text("Analizando alumno 3/20: Ana...", "en"),
            "Analyzing student 3/20: Ana...",
        )

    def test_translate_text_handles_icons_and_dynamic_status(self):
        self.assertEqual(i18n.translate_text("📋  Cursos", "en"), "📋  Courses")
        self.assertEqual(
            i18n.translate_text("Conectado: Campus — Selecciona un curso para analizar", "en"),
            "Connected: Campus — Select a course to analyze",
        )
        self.assertEqual(i18n.translate_text("  Sin conexión", "en"), "  Disconnected")
        self.assertEqual(
            i18n.translate_text("Eng: 82  |  Acceso: hoy  |  Entregas: 90%", "en"),
            "Eng: 82  | Access: hoy  | Submissions: 90%",
        )
        self.assertEqual(
            i18n.translate_text("Alumno: Ana | Riesgo: alto | Engagement: 72/100", "en"),
            "Student: Ana | Risk: high | Engagement: 72/100",
        )
        self.assertEqual(
            i18n.translate_text("Pico: Lunes a las 08h", "en"),
            "Peak: Monday at 08:00",
        )
        self.assertEqual(
            i18n.translate_text("Error HTTP al generar el informe IA: boom", "en"),
            "HTTP error while generating the AI report: boom",
        )
        self.assertEqual(
            i18n.translate_text(
                "Tienes 2 tarea(s) sin entregar. Consúltalas en la sección de tareas.",
                "en",
            ),
            "You have 2 assignment(s) not submitted. Check them in the assignments section.",
        )
        self.assertEqual(
            i18n.translate_text(
                "Participa en los foros del curso — son una buena oportunidad para resolver dudas.",
                "fr",
            ),
            "Participez aux forums du cours : c'est une bonne occasion de résoudre vos doutes.",
        )

    def test_semantic_section_key_accepts_multiple_languages(self):
        self.assertEqual(semantic_section_key("Executive summary"), "summary")
        self.assertEqual(semantic_section_key("Recommended actions"), "actions")
        self.assertEqual(semantic_section_key("Risques"), "risks")


if __name__ == "__main__":
    unittest.main()
