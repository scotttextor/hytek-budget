"""Build a single PDF with all trusses in a job — one truss per page.

Pipeline:
  1. Discover all <frame name="..." type="Truss"> in the FrameCAD XML
  2. For each truss, call viz_full_truss.render() to make an SVG
  3. Convert SVG → PDF page via svglib + reportlab
  4. Concat all pages with pypdf

Output: full_truss_review_<job>.pdf in scripts/.
"""
import os, re, io, sys, tempfile, subprocess

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, THIS_DIR)

from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF
from pypdf import PdfWriter, PdfReader

XML_PATH = r'C:/Users/Scott/OneDrive - Textor Metal Industries/Desktop/2603191 ROCKVILLE TH-TYPE-A1-LT-GF-LIN-89.075.xml'
SVG_TOOL = os.path.join(THIS_DIR, 'viz_full_truss.py')
OUT_PDF  = os.path.join(THIS_DIR, 'full_truss_review_2603191.pdf')

def discover_trusses(xml_path):
    with open(xml_path) as f:
        text = f.read()
    return re.findall(r'<frame\s+name="([^"]+)"\s+type="Truss"', text)

def main():
    trusses = discover_trusses(XML_PATH)
    print(f'Found {len(trusses)} trusses: {trusses}')

    writer = PdfWriter()
    tmpdir = tempfile.mkdtemp(prefix='trussreview_')

    for i, t in enumerate(trusses, 1):
        svg_name = f'_review_{t}.svg'
        pdf_name = f'_review_{t}.pdf'
        svg_path = os.path.join(THIS_DIR, svg_name)
        pdf_path = os.path.join(tmpdir, pdf_name)

        # Run the existing renderer to produce the SVG
        result = subprocess.run(
            [sys.executable, SVG_TOOL, '--truss', t, '--out', svg_name],
            capture_output=True, text=True, cwd=THIS_DIR,
        )
        if result.returncode != 0:
            print(f'  [{i}/{len(trusses)}] {t} FAILED: {result.stderr.strip()}')
            continue

        # Convert SVG → PDF
        try:
            drawing = svg2rlg(svg_path)
            renderPDF.drawToFile(drawing, pdf_path)
            reader = PdfReader(pdf_path)
            for page in reader.pages:
                writer.add_page(page)
            print(f'  [{i}/{len(trusses)}] {t}: SVG-to-PDF OK')
        except Exception as e:
            print(f'  [{i}/{len(trusses)}] {t} CONVERT FAILED: {e}')
        finally:
            # Clean up the per-truss SVG (keep only the per-truss PDFs in tmp)
            if os.path.exists(svg_path):
                os.remove(svg_path)

    with open(OUT_PDF, 'wb') as f:
        writer.write(f)
    print(f'\nWrote {OUT_PDF}  ({len(writer.pages)} pages)')

if __name__ == '__main__':
    main()
