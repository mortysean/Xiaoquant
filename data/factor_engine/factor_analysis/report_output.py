import os
import base64
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
import openai

from utils.utils import project_path

openai.api_key = os.getenv("OPENAI_API_KEY")

def gpt_analyze_image(image_path, prompt):
    try:
        print(f"🔍 [GPT] Calling GPT for image: {os.path.basename(image_path)}")
        print(f"📄 Prompt:\n{prompt}")
        with open(image_path, "rb") as f:
            base64_image = base64.b64encode(f.read()).decode("utf-8")
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a professional quant researcher and report writer."},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                    ]
                }
            ],
            max_tokens=800
        )
        result = response.choices[0].message.content.strip()
        print(f"✅ [GPT] Response:\n{result[:100]}...\n")
        return result
    except Exception as e:
        print(f"❌ GPT request failed:\n{e}")
        return f"(GPT ERROR) {str(e)}"

def build_prompt_for_section(section_title):
    prompts = {
        "performance": "Given the factor performance chart, analyze return distribution across quantiles. Comment on quantile separation and consistency. Is the factor predictive?",
        "ic": "Given the Information Coefficient chart, evaluate signal stability and IC quality. Comment on average IC and its decay.",
        "turnover": "Based on the turnover chart, assess factor frequency and temporal stability. Does the factor show excessive churn?",
        "summary": "Summarize all findings. Assess factor quality, robustness, and next steps for deployment."
    }
    key = "performance" if "performance" in section_title.lower() else \
          "ic" if "ic" in section_title.lower() else \
          "turnover" if "turnover" in section_title.lower() else \
          "summary" if "summary" in section_title.lower() else "performance"
    return prompts[key]

class FactorPDFReport:
    def __init__(self, factor_name, output_dir):
        self.factor_name = factor_name
        self.output_dir = output_dir
        self.pdf_path = project_path(output_dir, f"{factor_name}_report.pdf")
        self.section_images = {
            "Factor Performance": project_path(output_dir, "tear_sheet_performance.png"),
            "Information Coefficient": project_path(output_dir, "tear_sheet_ic.png"),
            "Turnover & Autocorrelation": project_path(output_dir, "tear_sheet_turnover.png"),
        }

    def clean_gpt_text(self, raw_text):
        import re
        text = re.sub(r"#+\s*", "", raw_text)  # Remove markdown headers like ###, ##
        text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)  # Remove bold
        text = re.sub(r"\s*-\s*", " - ", text)  # Normalize bullets
        text = re.sub(r"\n+", "\n", text)  # Remove repeated newlines
        return text.strip()

    def draw_wrapped_text(self, pdf, text, x_mm, y_mm, width_mm, font="Helvetica", fontsize=11, line_spacing=16):
        from reportlab.pdfbase.pdfmetrics import stringWidth
        import textwrap

        pdf.setFont(font, fontsize)
        max_width_pt = width_mm * mm
        y = y_mm * mm

        # 按双换行或标点加换行划分段落
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

        for para in paragraphs:
            # 中文分句（兼容中英文）
            if all(ord(char) < 128 for char in para):
                # 英文段落用 textwrap
                wrapped_lines = textwrap.wrap(para, width=9999)
                line = ""
                for word in para.split():
                    if stringWidth(line + " " + word, font, fontsize) <= max_width_pt:
                        line += (" " if line else "") + word
                    else:
                        pdf.drawString(x_mm * mm, y, line)
                        y -= line_spacing
                        line = word
                        if y < 30 * mm:
                            pdf.showPage()
                            pdf.setFont(font, fontsize)
                            y = (A4[1] - 40 * mm)
                if line:
                    pdf.drawString(x_mm * mm, y, line)
                    y -= line_spacing
            else:
                # 中文段落按每40字符分行
                zh_lines = textwrap.wrap(para, width=40)
                for line in zh_lines:
                    pdf.drawString(x_mm * mm, y, line)
                    y -= line_spacing
                    if y < 30 * mm:
                        pdf.showPage()
                        pdf.setFont(font, fontsize)
                        y = (A4[1] - 40 * mm)

            # 段落之间添加额外空行
            y -= line_spacing


    def generate(self):
        print(f"📜 Creating PDF report for factor: {self.factor_name}")
        pdf = canvas.Canvas(self.pdf_path, pagesize=A4)
        width, height = A4

        # Title Page
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawCentredString(width / 2, height - 50, f"Factor Analysis Report: {self.factor_name}")
        pdf.setFont("Helvetica", 12)
        pdf.drawString(40, height - 100, "This report presents the analysis of the factor using tear sheet charts and GPT-generated insights.")
        pdf.showPage()

        # Section Pages
        for section_title, image_path in self.section_images.items():
            print(f"🖼 Generating section: {section_title}")
            gpt_text = gpt_analyze_image(image_path, build_prompt_for_section(section_title))
            gpt_text = self.clean_gpt_text(gpt_text)

            # Page 1: Chart
            pdf.setFont("Helvetica-Bold", 14)
            pdf.drawString(40, height - 50, section_title)
            with Image.open(image_path) as img:
                img_w, img_h = img.size
                target_width_mm = 80
                display_width = target_width_mm * mm
                scale = display_width / img_w
                display_height = img_h * scale
                x = (width - display_width) / 2
                y_img = height - 80 - display_height
                pdf.drawImage(ImageReader(img), x, y_img, width=display_width, height=display_height)
            pdf.showPage()

            # Page 2: Text
            pdf.setFont("Helvetica-Bold", 14)
            pdf.drawString(40, height - 50, f"{section_title} - GPT Analysis")
            self.draw_wrapped_text(pdf, gpt_text, x_mm=20, y_mm=(height - 80) / mm, width_mm=170, fontsize=11, line_spacing=15)
            pdf.showPage()

        # Summary Page
        summary_text = gpt_analyze_image(self.section_images["Factor Performance"], build_prompt_for_section("summary"))
        summary_text = self.clean_gpt_text(summary_text)

        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(40, height - 50, "Summary Interpretation")
        self.draw_wrapped_text(pdf, summary_text, x_mm=20, y_mm=(height - 80) / mm, width_mm=170, fontsize=11, line_spacing=15)

        pdf.save()
        print(f"✅ Report saved to: {self.pdf_path}")
        return self.pdf_path
