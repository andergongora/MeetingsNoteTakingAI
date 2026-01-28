"""
Meeting analysis module using Google Gemini API
"""
import json
from pathlib import Path
import google.generativeai as genai
from .config import Config


class MeetingAnalyzer:
    """Analyzes meeting transcripts using Google Gemini"""

    def __init__(self):
        genai.configure(api_key=Config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(Config.GEMINI_MODEL)

    def _load_prompt_template(self) -> str:
        """Load the prompt template from file"""
        prompt_file = Config.PROMPTS_DIR / "meeting_analysis.txt"

        if prompt_file.exists():
            with open(prompt_file, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            # Default prompt if file doesn't exist
            print(f"⚠ No se encontró el archivo de prompts en {prompt_file}. Usando prompt por defecto.")
            return """Eres un asistente especializado en análisis de reuniones.

Analiza la siguiente transcripción y extrae:

1. **Notas Clave**: Puntos importantes y decisiones tomadas
2. **Tareas para Ander**: Acciones específicas asignadas a Ander
3. **Resumen Ejecutivo**: Resumen conciso (2-3 párrafos)

TRANSCRIPCIÓN:
---
{transcript}
---

Responde en formato JSON con esta estructura exacta:
{{
  "notas": ["nota 1", "nota 2"],
  "tareas_para_ander": ["tarea 1", "tarea 2"],
  "resumen": "Resumen ejecutivo"
}}
"""

    def analyze(self, transcript: str) -> dict:
        """
        Analyze meeting transcript with Gemini

        Args:
            transcript: The meeting transcript text

        Returns:
            Dictionary with notes, tasks, and summary
        """
        print()
        print("="*70)
        print("🤖 ANALIZANDO CON GEMINI")
        print("="*70)
        print(f"📝 Longitud del transcript: {len(transcript)} caracteres")
        print(f"🤖 Modelo: {Config.GEMINI_MODEL}")
        print()
        print("⏳ Enviando a Gemini API...")

        # Load and format prompt
        prompt_template = self._load_prompt_template()
        prompt = prompt_template.format(transcript=transcript)

        # Generate response
        response = self.model.generate_content(prompt)

        print("✓ Análisis completado")
        print()

        # Parse JSON response
        try:
            # Extract JSON from response (may be wrapped in markdown code blocks)
            text = response.text.strip()

            # Remove markdown code blocks if present
            if text.startswith("```json"):
                text = text[7:]  # Remove ```json
            elif text.startswith("```"):
                text = text[3:]  # Remove ```

            if text.endswith("```"):
                text = text[:-3]  # Remove closing ```

            text = text.strip()

            result = json.loads(text)

            # Validate structure
            required_keys = ["notas", "tareas_para_ander", "resumen"]
            if not all(key in result for key in required_keys):
                raise ValueError("Response missing required keys")

            return result

        except (json.JSONDecodeError, ValueError) as e:
            print(f"⚠ Error parseando respuesta JSON: {e}")
            print("📄 Respuesta raw de Gemini:")
            print(response.text)

            # Return default structure
            return {
                "notas": ["Error al parsear respuesta de Gemini"],
                "tareas_para_ander": [],
                "resumen": response.text
            }

    def format_markdown(self, analysis: dict) -> str:
        """
        Format analysis as readable Markdown

        Args:
            analysis: Analysis dictionary from analyze()

        Returns:
            Formatted markdown string
        """
        md = "# Resumen de Reunión\n\n"

        # Summary
        md += "## 📋 Resumen Ejecutivo\n\n"
        md += analysis.get("resumen", "No disponible") + "\n\n"

        # Notes
        md += "## 📝 Notas Clave\n\n"
        notas = analysis.get("notas", [])
        if notas:
            for nota in notas:
                md += f"- {nota}\n"
        else:
            md += "*No hay notas disponibles*\n"
        md += "\n"

        # Tasks
        md += "## ✅ Tareas para Ander\n\n"
        tareas = analysis.get("tareas_para_ander", [])
        if tareas:
            for tarea in tareas:
                md += f"- [ ] {tarea}\n"
        else:
            md += "*No hay tareas asignadas*\n"
        md += "\n"

        return md

    def save_analysis(self, analysis: dict, output_path: Path) -> tuple[Path, Path]:
        """
        Save analysis in both JSON and Markdown formats

        Args:
            analysis: Analysis dictionary
            output_path: Base path for output files (without extension)

        Returns:
            Tuple of (json_path, markdown_path)
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save as JSON
        json_path = output_path.with_suffix('.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2)

        # Save as Markdown
        md_path = output_path.with_suffix('.md')
        markdown = self.format_markdown(analysis)
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(markdown)

        print(f"💾 Análisis guardado:")
        print(f"   JSON: {json_path}")
        print(f"   Markdown: {md_path}")
        print()

        return json_path, md_path
