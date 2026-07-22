use std::collections::HashMap;
use std::env;
use std::fs;
use physure_script::value::{PhsValue, PlotData};
use crate::step::ExecutionStep;

pub fn open_standalone_html(title: &str, code: &str, steps: &[ExecutionStep], vars: &HashMap<String, PhsValue>) -> Result<(), Box<dyn std::error::Error>> {
    let mut temp_dir = env::temp_dir();
    let file_name = format!("physure_{}.html", std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH)?.as_secs());
    temp_dir.push(file_name);

    let mut steps_html = String::new();
    for (i, step) in steps.iter().enumerate() {
        if step.is_display_text {
            if let PhsValue::String(ref text) = step.value {
                steps_html.push_str(&format!(
                    r#"<div class="my-4 p-4 bg-slate-900 border-l-4 border-cyan-500 rounded-r-lg shadow-md">
                        <div class="text-xs uppercase font-mono text-cyan-400 mb-1">Documentation Block #{}</div>
                        <div class="text-sm text-slate-200 whitespace-pre-wrap font-sans">{}</div>
                    </div>"#, i + 1, text
                ));
            }
            continue;
        }

        match &step.value {
            PhsValue::Plot(PlotData { title: p_title, svg, .. }) => {
                steps_html.push_str(&format!(
                    r#"<div class="my-6 bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl">
                        <h3 class="text-md font-semibold text-cyan-400 mb-3 flex items-center gap-2">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18"/></svg>
                            {}
                        </h3>
                        <div class="overflow-x-auto bg-slate-950 p-4 rounded-lg flex justify-center border border-slate-800 shadow-inner">
                            {}
                        </div>
                    </div>"#, p_title, svg
                ));
            }
            _ => {
                let val_str = step.value.to_string();
                if !val_str.is_empty() {
                    steps_html.push_str(&format!(
                        r#"<tr class="hover:bg-slate-900/50 transition">
                            <td class="py-3 px-2 font-mono text-cyan-400 font-bold whitespace-nowrap">{}</td>
                            <td class="py-3 px-2 font-mono text-slate-300">{}</td>
                            <td class="py-3 px-2 font-mono text-amber-300 font-semibold">{}</td>
                            <td class="py-3 px-2 text-right">
                                <button onclick="navigator.clipboard.writeText('{} = {}')" class="px-3 py-1 bg-slate-800 hover:bg-cyan-600 text-xs rounded-md text-slate-200 font-medium transition shadow">Copy</button>
                            </td>
                        </tr>"#,
                        step.label, step.expr_code, val_str, step.label, val_str
                    ));
                }
            }
        }
    }

    let mut vars_html = String::new();
    for (k, v) in vars {
        let val_str = v.to_string();
        vars_html.push_str(&format!(
            r#"<div class="p-3 bg-slate-900 border border-slate-800 rounded-lg flex justify-between items-center shadow-sm">
                <div>
                    <span class="font-mono font-bold text-cyan-400 text-sm">{}</span>
                    <span class="text-slate-400 mx-2 text-xs">=</span>
                    <span class="font-mono text-amber-300 font-medium text-sm">{}</span>
                </div>
                <button onclick="navigator.clipboard.writeText('{} = {}')" class="px-2.5 py-1 bg-slate-800 hover:bg-cyan-600 text-xs rounded text-slate-200 transition">Copy</button>
            </div>"#,
            k, val_str, k, val_str
        ));
    }

    let html_content = format!(r#"
<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Physure Report - {}</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen p-6 font-sans">
    <div class="max-w-7xl mx-auto space-y-8">
        <header class="flex justify-between items-center border-b border-slate-800 pb-4">
            <div>
                <h1 class="text-3xl font-bold bg-gradient-to-r from-cyan-400 via-blue-500 to-indigo-400 bg-clip-text text-transparent">Physure Engine Report</h1>
                <p class="text-slate-400 text-sm mt-1">Script: <code class="text-cyan-400 font-mono">{}</code> | Standalone Zero-Server Report</p>
            </div>
            <span class="px-3 py-1 bg-cyan-950 border border-cyan-800 text-cyan-400 text-xs rounded-full font-mono">file:// Standalone</span>
        </header>

        <div class="grid grid-cols-1 lg:grid-cols-12 gap-8">
            <!-- Left: PHS Code & Final Variables -->
            <div class="lg:col-span-5 space-y-6">
                <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl">
                    <h2 class="text-lg font-semibold text-cyan-400 mb-3 flex items-center gap-2">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"/></svg>
                        Source PHS Script
                    </h2>
                    <pre class="bg-slate-950 p-4 rounded-lg font-mono text-xs text-slate-300 overflow-x-auto border border-slate-800 max-h-[500px]">{}</pre>
                </div>

                <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl">
                    <h2 class="text-lg font-semibold text-emerald-400 mb-3 flex items-center gap-2">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"/></svg>
                        Final State Variables
                    </h2>
                    <div class="space-y-2 max-h-[400px] overflow-y-auto pr-1">
                        {}
                    </div>
                </div>
            </div>

            <!-- Right: Step-by-Step Calculations & Plots -->
            <div class="lg:col-span-7 space-y-6">
                <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl">
                    <h2 class="text-lg font-semibold text-amber-400 mb-4 flex items-center gap-2">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z"/></svg>
                        Step-by-Step Calculation Trace
                    </h2>
                    <div class="overflow-x-auto">
                        <table class="w-full text-left text-sm border-collapse">
                            <thead>
                                <tr class="border-b border-slate-800 text-slate-400 font-semibold text-xs uppercase">
                                    <th class="pb-3 px-2">Label / Target</th>
                                    <th class="pb-3 px-2">Expression</th>
                                    <th class="pb-3 px-2">Evaluated Result</th>
                                    <th class="pb-3 px-2 text-right">Action</th>
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-slate-800/60">
                                {}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
    "#, title, title, code, vars_html, steps_html);

    fs::write(&temp_dir, html_content)?;
    println!("\x1b[1;32m📄 Generated standalone HTML report:\x1b[0m {}", temp_dir.display());
    open::that(&temp_dir)?;
    Ok(())
}
