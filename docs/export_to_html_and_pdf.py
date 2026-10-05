import os
import json
import subprocess
from pathlib import Path

def generate_html_viewer():
    md_path = Path("docs/Planteamiento_Proyecto.md")
    html_out = Path("docs/Planteamiento_Proyecto_Imprimible.html")
    
    if not md_path.exists():
        print(f"Error: No se encontró {md_path}")
        return

    with open(md_path, "r", encoding="utf-8") as f:
        md_content = f.read()

    # Escapar contenido markdown para embeberlo con total seguridad en JavaScript
    escaped_md = json.dumps(md_content)

    html_template = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>PA_E1_Planteamiento_QuickDeliverySim</title>
  
  <!-- MathJax 3 para renderizado perfecto de LaTeX -->
  <script>
    window.MathJax = {{
      tex: {{
        inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
        displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']],
        processEscapes: true
      }},
      options: {{
        skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code']
      }}
    }};
  </script>
  <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js" id="MathJax-script" async></script>

  <!-- Marked.js para compilar Markdown a HTML en el cliente -->
  <script src="https://cdn.jsdelivr.net/npm/marked@9.1.6/marked.min.js"></script>

  <!-- Mermaid.js para renderizar los diagramas de arquitectura, flujo y clases -->
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.0/dist/mermaid.min.js"></script>
  <script>
    mermaid.initialize({{
      startOnLoad: false,
      theme: 'default',
      securityLevel: 'loose',
      flowchart: {{ useMaxWidth: false, htmlLabels: true }},
      classDiagram: {{ useMaxWidth: false }}
    }});
  </script>

  <style>
    @import url('https://fonts.googleapis.com/css2?family=Segoe+UI:ital,wght@0,300;0,400;0,600;0,700;1,400&family=JetBrains+Mono:wght@400;500&display=swap');

    :root {{
      --primary-color: #1a365d;
      --secondary-color: #2b6cb0;
      --border-color: #e2e8f0;
      --bg-alt: #f8fafc;
      --text-main: #2d3748;
    }}

    body {{
      font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
      font-size: 11pt;
      line-height: 1.15;
      color: var(--text-main);
      background-color: #f1f5f9;
      margin: 0;
      padding: 20px;
    }}

    .container {{
      max-width: 920px;
      margin: 0 auto;
      background: white;
      padding: 40px 50px;
      border-radius: 8px;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }}

    .caption {{
      font-size: 9.5pt;
      font-weight: 600;
      text-align: center;
      margin: 8px 0 16px 0;
      color: var(--primary-color);
    }}

    /* Estilos de Tipografía y Encabezados */
    h1 {{
      font-size: 20pt;
      color: var(--primary-color);
      border-bottom: 2px solid var(--primary-color);
      padding-bottom: 8px;
      margin-top: 0;
      page-break-after: avoid;
      break-after: avoid;
    }}

    h2 {{
      font-size: 15pt;
      color: var(--secondary-color);
      border-bottom: 1px solid var(--border-color);
      padding-bottom: 6px;
      margin-top: 28px;
      page-break-after: avoid;
      break-after: avoid;
    }}

    h3 {{
      font-size: 12.5pt;
      color: #2c5282;
      margin-top: 20px;
      page-break-after: avoid;
      break-after: avoid;
    }}

    h4 {{
      font-size: 11.5pt;
      color: #3182ce;
      margin-top: 16px;
      page-break-after: avoid;
      break-after: avoid;
    }}

    p, li {{
      text-align: justify;
      margin-bottom: 8px;
    }}

    blockquote {{
      border-left: 4px solid var(--secondary-color);
      background-color: var(--bg-alt);
      margin: 14px 0;
      padding: 10px 16px;
      font-style: italic;
      color: #4a5568;
      border-radius: 0 4px 4px 0;
      page-break-inside: avoid;
      break-inside: avoid;
    }}

    hr {{
      border: 0;
      height: 1px;
      background: #e2e8f0;
      margin: 22px 0;
    }}

    /* Tablas Optimizadas: NO forzar page-break-inside en la tabla completa para evitar hojas en blanco */
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 16px 0;
      font-size: 9pt;
      page-break-inside: auto;
      break-inside: auto;
    }}

    thead {{
      display: table-header-group;
    }}

    tr {{
      page-break-inside: avoid;
      break-inside: avoid;
    }}

    th, td {{
      border: 1px solid #cbd5e1;
      padding: 6px 8px;
      text-align: left;
      vertical-align: middle;
    }}

    th {{
      background-color: #edf2f7;
      color: var(--primary-color);
      font-weight: 600;
    }}

    tr:nth-child(even) {{
      background-color: var(--bg-alt);
    }}

    /* Diagramas Mermaid */
    .mermaid {{
      text-align: center;
      margin: 18px auto;
      background: #ffffff;
      padding: 8px;
      border-radius: 6px;
      border: 1px solid #e2e8f0;
      page-break-inside: auto;
      break-inside: auto;
      overflow-x: auto;
    }}

    .mermaid svg {{
      max-width: 100% !important;
      height: auto !important;
      display: block;
      margin: 0 auto;
    }}

    /* Código */
    code {{
      font-family: 'JetBrains Mono', Consolas, monospace;
      font-size: 9pt;
      background-color: #f1f5f9;
      color: #c53030;
      padding: 2px 4px;
      border-radius: 3px;
    }}

    pre {{
      background-color: #1e293b;
      color: #f8fafc;
      padding: 12px;
      border-radius: 6px;
      overflow-x: auto;
      font-size: 9pt;
      page-break-inside: auto;
      break-inside: auto;
    }}

    pre code {{
      background-color: transparent;
      color: inherit;
      padding: 0;
    }}

    /* Configuración especial para impresión / PDF */
    @media print {{
      body {{
        background: white;
        padding: 0;
        font-size: 11pt !important;
        line-height: 1.15 !important;
      }}
      .container {{
        max-width: 100%;
        padding: 0;
        box-shadow: none;
        border-radius: 0;
      }}
      @page {{
        size: letter;
        margin: 14mm 12mm 14mm 12mm;
      }}
      .no-print {{
        display: none !important;
      }}
      h1, h2, h3, h4 {{
        page-break-after: avoid;
        break-after: avoid;
      }}
      /* Fluidos sin forzar saltos masivos */
      .mermaid, pre {{
        page-break-inside: auto !important;
        break-inside: auto !important;
      }}
      .mermaid svg {{
        max-width: 100% !important;
        max-height: 220mm !important;
        height: auto !important;
      }}
      table {{
        page-break-inside: auto !important;
        break-inside: auto !important;
      }}
      tr {{
        page-break-inside: avoid !important;
        break-inside: avoid !important;
      }}
      blockquote {{
        page-break-inside: avoid;
        break-inside: avoid;
      }}
      a {{
        color: #2b6cb0;
        text-decoration: none;
      }}
    }}

    .banner-print {{
      background: #ebf8ff;
      border: 1px solid #bee3f8;
      color: #2b6cb0;
      padding: 12px 18px;
      border-radius: 6px;
      margin-bottom: 20px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .btn-print {{
      background: #3182ce;
      color: white;
      border: none;
      padding: 8px 16px;
      font-size: 11pt;
      font-weight: 600;
      border-radius: 4px;
      cursor: pointer;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }}
    .btn-print:hover {{
      background: #2b6cb0;
    }}
  </style>
</head>
<body>

  <div class="container">
    <div class="banner-print no-print">
      <div>
        <strong>📄 Vista Optimizada para Exportar a PDF (Cero Deformación):</strong><br>
        <span style="font-size: 9.5pt;">Fórmulas LaTeX protegidas y diagramas vectoriales escalados dinámicamente.</span>
      </div>
      <button class="btn-print" onclick="window.print()">🖨️ Guardar como PDF (Ctrl+P)</button>
    </div>

    <div id="content">Cargando y procesando documento...</div>
  </div>

  <script>
    const markdownContent = {escaped_md};

    async function renderDocument() {{
      const contentDiv = document.getElementById('content');

      // 1. Configurar marked renderer para interceptar bloques mermaid
      const renderer = new marked.Renderer();
      const defaultCode = renderer.code.bind(renderer);

      renderer.code = function(code, lang) {{
        if (lang === 'mermaid') {{
          return `<div class="mermaid">${{code}}</div>`;
        }}
        return defaultCode(code, lang);
      }};

      marked.setOptions({{
        renderer: renderer,
        gfm: true,
        breaks: false
      }});

      // 2. CRUCIAL: Proteger ecuaciones LaTeX antes de ejecutar marked.parse
      // Esto evita que marked confunda subíndices como _listo o _cocina con etiquetas <em>
      const displayMathList = [];
      let sanitizedMd = markdownContent.replace(/\\$\\$([\\s\\S]*?)\\$\\$/g, function(match) {{
        displayMathList.push(match);
        return `@@@MATH_DISPLAY_${{displayMathList.length - 1}}@@@`;
      }});

      const inlineMathList = [];
      sanitizedMd = sanitizedMd.replace(/(?<!\\\\)\\$([^$\\n]+?)(?<!\\\\)\\$/g, function(match) {{
        inlineMathList.push(match);
        return `@@@MATH_INLINE_${{inlineMathList.length - 1}}@@@`;
      }});

      // 3. Compilar markdown seguro a HTML
      let html = marked.parse(sanitizedMd);

      // 4. Restaurar fórmulas matemáticas LaTeX intactas (limpiando barras invertidas accidentales ante guiones bajos)
      html = html.replace(/@@@MATH_DISPLAY_(\\d+)@@@/g, function(_, idx) {{
        let math = displayMathList[parseInt(idx, 10)];
        return math.replace(/\\\\_/g, '_');
      }});
      html = html.replace(/@@@MATH_INLINE_(\\d+)@@@/g, function(_, idx) {{
        let math = inlineMathList[parseInt(idx, 10)];
        return math.replace(/\\\\_/g, '_');
      }});

      contentDiv.innerHTML = html;

      // 5. Renderizar diagramas de Mermaid
      try {{
        await mermaid.run({{
          querySelector: '.mermaid'
        }});
      }} catch (err) {{
        console.error('Error al renderizar Mermaid:', err);
      }}

      // 6. Renderizar MathJax para ecuaciones KaTeX/LaTeX
      if (window.MathJax && window.MathJax.typesetPromise) {{
        try {{
          await window.MathJax.typesetPromise([contentDiv]);
        }} catch (err) {{
          console.error('Error al renderizar MathJax:', err);
        }}
      }}
    }}

    window.addEventListener('DOMContentLoaded', renderDocument);
  </script>
</body>
</html>
"""

    with open(html_out, "w", encoding="utf-8") as f:
        f.write(html_template)
    
    print(f"Archivo HTML imprimible regenerado exitosamente en: {html_out}")
    return html_out

if __name__ == "__main__":
    generate_html_viewer()
