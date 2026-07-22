use std::collections::HashMap;
use std::env;
use std::fs;
use physure_script::value::PhsValue;

pub fn open_standalone_html(title: &str, code: &str, vars: &HashMap<String, PhsValue>) -> Result<(), Box<dyn std::error::Error>> {
    let mut temp_dir = env::temp_dir();
    let file_name = format!("physure_{}.html", std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH)?.as_secs());
    temp_dir.push(file_name);

    let mut rows_html = String::new();
    for (k, v) in vars {
        let val_str = v.to_string();
        rows_html.push_str(&format!(
            "<tr><td class='py-3 font-mono text-cyan-400 font-bold'>{}</td><td class='py-3 font-mono text-amber-300'>{}</td><td class='py-3'><button onclick=\"navigator.clipboard.writeText('{} = {}')\" class='px-3 py-1 bg-slate-800 hover:bg-cyan-600 text-xs rounded-md text-white font-medium transition shadow'>Copy</button></td></tr>",
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
<body class="bg-slate-950 text-slate-100 min-h-screen p-8 font-sans">
    <div class="max-w-6xl mx-auto space-y-6">
        <header class="flex justify-between items-center border-b border-slate-800 pb-4">
            <div>
                <h1 class="text-3xl font-bold bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">Physure Standalone Report</h1>
                <p class="text-slate-400 text-sm">Target: {} | Zero-Server Standalone Viewer</p>
            </div>
            <span class="px-3 py-1 bg-cyan-950 border border-cyan-800 text-cyan-400 text-xs rounded-full font-mono">file:// Offline</span>
        </header>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl flex flex-col">
                <h2 class="text-lg font-semibold text-cyan-400 mb-3">PHS Source Code</h2>
                <pre class="bg-slate-950 p-4 rounded-lg font-mono text-sm text-slate-300 overflow-x-auto border border-slate-800 flex-1">{}</pre>
            </div>

            <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl flex flex-col">
                <h2 class="text-lg font-semibold text-emerald-400 mb-3">Quantities & Results</h2>
                <div class="overflow-x-auto flex-1">
                    <table class="w-full text-left text-sm border-collapse">
                        <thead>
                            <tr class="border-b border-slate-800 text-slate-400 font-semibold">
                                <th class="pb-2">Variable</th>
                                <th class="pb-2">Value</th>
                                <th class="pb-2">Action</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-800/50">
                            {}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
    "#, title, title, code, rows_html);

    fs::write(&temp_dir, html_content)?;
    println!("\x1b[1;32m📄 Generated standalone HTML report:\x1b[0m {}", temp_dir.display());
    open::that(&temp_dir)?;
    Ok(())
}
