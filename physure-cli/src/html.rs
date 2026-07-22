use std::collections::HashMap;
use std::env;
use std::fs;
use physure_script::value::{PhsValue, PlotData};
use crate::step::ExecutionStep;

struct ScriptMetadata {
    title: Option<String>,
    author: Option<String>,
    institution: Option<String>,
    date: Option<String>,
    abstract_text: Option<String>,
}

fn extract_metadata(code: &str) -> ScriptMetadata {
    let mut meta = ScriptMetadata {
        title: None,
        author: None,
        institution: None,
        date: None,
        abstract_text: None,
    };
    for line in code.lines() {
        let trimmed = line.trim();
        if trimmed.starts_with("# @title:") {
            meta.title = Some(trimmed.trim_start_matches("# @title:").trim().to_string());
        } else if trimmed.starts_with("# @author:") {
            meta.author = Some(trimmed.trim_start_matches("# @author:").trim().to_string());
        } else if trimmed.starts_with("# @institution:") {
            meta.institution = Some(trimmed.trim_start_matches("# @institution:").trim().to_string());
        } else if trimmed.starts_with("# @date:") {
            meta.date = Some(trimmed.trim_start_matches("# @date:").trim().to_string());
        } else if trimmed.starts_with("# @abstract:") {
            meta.abstract_text = Some(trimmed.trim_start_matches("# @abstract:").trim().to_string());
        }
    }
    meta
}

fn escape_html(input: &str) -> String {
    input
        .replace('&', "&amp;")
        .replace('<', "&lt;")
        .replace('>', "&gt;")
        .replace('"', "&quot;")
}

pub fn open_standalone_html(title: &str, code: &str, steps: &[ExecutionStep], vars: &HashMap<String, PhsValue>) -> Result<(), Box<dyn std::error::Error>> {
    let mut temp_dir = env::temp_dir();
    let file_name = format!("physure_{}.html", std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH)?.as_secs());
    temp_dir.push(file_name);

    let meta = extract_metadata(code);
    let paper_title = meta.title.clone().unwrap_or_else(|| title.to_string());
    let paper_inst = meta.institution.clone().unwrap_or_else(|| "Physure Technical & Academic Computation Report".to_string());
    let paper_author = meta.author.clone().unwrap_or_else(|| "Physure Engine".to_string());
    let paper_date = meta.date.clone().unwrap_or_else(|| {
        chrono::Local::now().format("%B %d, %Y").to_string()
    });

    let mut abstract_html = String::new();
    if let Some(ref abs_text) = meta.abstract_text {
        abstract_html = format!(
            r#"<div class="latex-abstract">
                <div class="abstract-title">Resumen / Abstract</div>
                <p>{}</p>
            </div>"#,
            escape_html(abs_text)
        );
    }

    let mut steps_html = String::new();
    let mut fig_counter = 1;

    for (i, step) in steps.iter().enumerate() {
        if step.is_display_text {
            if let PhsValue::String(ref text) = step.value {
                steps_html.push_str(&format!(
                    r#"<div class="latex-prose">
                        <p>{}</p>
                    </div>"#,
                    escape_html(text).replace("\n", "<br/>")
                ));
            }
            continue;
        }

        match &step.value {
            PhsValue::Plot(PlotData { title: p_title, svg, .. }) => {
                steps_html.push_str(&format!(
                    r#"<figure class="latex-figure">
                        <div class="fig-frame">
                            {}
                        </div>
                        <figcaption class="fig-caption">
                            <strong>Figura {}.</strong> {} (Paso {}).
                        </figcaption>
                    </figure>"#,
                    svg, fig_counter, escape_html(p_title), i + 1
                ));
                fig_counter += 1;
            }
            _ => {
                let val_str = step.value.to_string();
                if !val_str.is_empty() {
                    steps_html.push_str(&format!(
                        r#"<tr>
                            <td><code>{}</code></td>
                            <td><code>{}</code></td>
                            <td><strong>{}</strong></td>
                        </tr>"#,
                        escape_html(&step.label),
                        escape_html(&step.expr_code),
                        escape_html(&val_str)
                    ));
                }
            }
        }
    }

    let mut vars_html = String::new();
    for (k, v) in vars {
        let val_str = v.to_string();
        vars_html.push_str(&format!(
            r#"<tr>
                <td><code>{}</code></td>
                <td><strong>{}</strong></td>
            </tr>"#,
            escape_html(k), escape_html(&val_str)
        ));
    }

    let html_content = format!(r#"<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{} &mdash; Reporte Técnico Physure</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.css">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Crimson+Pro:ital,wght@0,400;0,600;0,700;1,400;1,600&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet">
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.js"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/contrib/auto-render.min.js"
        onload="renderMathInElement(document.body);"></script>
    <style>
        @page {{
            size: A4;
            margin: 25mm 20mm;
        }}

        body {{
            font-family: 'Crimson Pro', 'Georgia', 'Times New Roman', serif;
            font-size: 11pt;
            color: #111111;
            background-color: #ffffff;
            line-height: 1.6;
            margin: 0;
            padding: 40px 20px;
        }}

        .paper-manuscript {{
            max-width: 840px;
            margin: 0 auto;
            background: #ffffff;
            padding: 0;
        }}

        .no-print-bar {{
            display: flex;
            justify-content: flex-end;
            margin-bottom: 24px;
        }}

        .btn-print {{
            font-family: system-ui, sans-serif;
            background: #ffffff;
            color: #333333;
            border: 1px solid #999999;
            padding: 6px 16px;
            font-size: 0.85rem;
            cursor: pointer;
            border-radius: 4px;
            transition: all 0.2s ease;
        }}

        .btn-print:hover {{
            background: #f4f4f4;
            border-color: #000000;
        }}

        .paper-header {{
            text-align: center;
            border-top: 1.5pt solid #000000;
            border-bottom: 1.5pt solid #000000;
            padding: 20px 0 16px 0;
            margin-bottom: 32px;
        }}

        .paper-institution {{
            font-family: system-ui, sans-serif;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            color: #555555;
            margin-bottom: 8px;
        }}

        .paper-title {{
            font-size: 2.1rem;
            font-weight: 700;
            margin: 0 0 10px 0;
            line-height: 1.2;
            color: #000000;
        }}

        .paper-author-meta {{
            font-style: italic;
            font-size: 0.95rem;
            color: #333333;
        }}

        .latex-abstract {{
            width: 90%;
            margin: 0 auto 36px auto;
            font-size: 0.95rem;
            font-style: italic;
            line-height: 1.6;
            text-align: justify;
            border-left: 2.5pt solid #000000;
            padding-left: 18px;
        }}

        .abstract-title {{
            font-family: system-ui, sans-serif;
            font-size: 0.8rem;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 1.2px;
            margin-bottom: 6px;
            font-style: normal;
            color: #000000;
        }}

        h2.paper-sec-title {{
            font-size: 1.25rem;
            font-weight: 700;
            border-bottom: 0.75pt solid #000000;
            padding-bottom: 4px;
            margin-top: 36px;
            margin-bottom: 16px;
            color: #000000;
        }}

        .booktabs {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.95rem;
            margin: 20px 0 32px 0;
        }}

        .booktabs th {{
            border-top: 1.5pt solid #000000;
            border-bottom: 0.75pt solid #000000;
            padding: 8px 10px;
            text-align: left;
            font-weight: bold;
            color: #000000;
        }}

        .booktabs td {{
            padding: 8px 10px;
            border-bottom: none;
            color: #111111;
        }}

        .booktabs tr:last-child td {{
            border-bottom: 1.5pt solid #000000;
        }}

        .booktabs code {{
            font-family: 'Fira Code', 'Courier New', monospace;
            font-size: 0.88rem;
        }}

        .latex-prose {{
            font-size: 1.05rem;
            line-height: 1.7;
            margin: 20px 0;
            text-align: justify;
        }}

        .latex-figure {{
            margin: 28px 0;
            text-align: center;
        }}

        .fig-frame {{
            border: 0.75pt solid #cccccc;
            padding: 12px;
            background: #fafafa;
            display: inline-block;
            max-width: 100%;
            border-radius: 4px;
        }}

        .fig-caption {{
            font-size: 0.88rem;
            color: #444444;
            margin-top: 8px;
            font-style: italic;
        }}

        .source-code-box {{
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 4px;
            padding: 16px;
            font-family: 'Fira Code', monospace;
            font-size: 0.85rem;
            white-space: pre-wrap;
            overflow-x: auto;
            color: #212529;
            margin-bottom: 32px;
        }}

        @media print {{
            .no-print-bar {{
                display: none;
            }}
            body {{
                padding: 0;
            }}
        }}
    </style>
</head>
<body>
    <div class="paper-manuscript">
        <div class="no-print-bar">
            <button class="btn-print" onclick="window.print()">🖨️ Guardar Reporte PDF / Imprimir</button>
        </div>

        <header class="paper-header">
            <div class="paper-institution">{}</div>
            <h1 class="paper-title">{}</h1>
            <div class="paper-author-meta">{} &bull; {} &bull; Motor Physure Core</div>
        </header>

        {}

        <h2 class="paper-sec-title">1. Memoria de Cálculos y Evaluaciones Físicas</h2>
        <table class="booktabs">
            <thead>
                <tr>
                    <th style="width: 25%;">Variable / Objetivo</th>
                    <th style="width: 40%;">Expresión Evaluada</th>
                    <th style="width: 35%;">Resultado Obtenido</th>
                </tr>
            </thead>
            <tbody>
                {}
            </tbody>
        </table>

        <h2 class="paper-sec-title">2. Estado Final de Variables</h2>
        <table class="booktabs">
            <thead>
                <tr>
                    <th style="width: 35%;">Variable</th>
                    <th style="width: 65%;">Valor Final</th>
                </tr>
            </thead>
            <tbody>
                {}
            </tbody>
        </table>

        <h2 class="paper-sec-title">3. Código Fuente PHS</h2>
        <pre class="source-code-box">{}</pre>
    </div>
</body>
</html>
    "#,
        escape_html(&paper_title),
        escape_html(&paper_inst),
        escape_html(&paper_title),
        escape_html(&paper_author),
        escape_html(&paper_date),
        abstract_html,
        steps_html,
        vars_html,
        escape_html(code)
    );

    fs::write(&temp_dir, html_content)?;
    println!("\x1b[1;32m📄 Reporte académico HTML generado:\x1b[0m {}", temp_dir.display());
    open::that(&temp_dir)?;
    Ok(())
}
