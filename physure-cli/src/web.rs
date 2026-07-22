use std::collections::HashMap;
use tiny_http::{Response, Server};
use physure_script::value::PhsValue;

pub fn start_web_server(code: &str, vars: &HashMap<String, PhsValue>) -> Result<(), Box<dyn std::error::Error>> {
    let server = Server::http("127.0.0.1:3000").map_err(|e| format!("{}", e))?;
    println!("\x1b[1;32m🚀 Physure Web Visualizer running at http://localhost:3000\x1b[0m");
    println!("\x1b[90mPress Ctrl+C to stop the server\x1b[0m");
    let _ = open::that("http://localhost:3000");

    let mut rows_html = String::new();
    for (k, v) in vars {
        let val_str = v.to_string();
        rows_html.push_str(&format!(
            "<tr><td class='py-2 font-mono text-cyan-400 font-bold'>{}</td><td class='py-2 font-mono text-amber-300'>{}</td><td class='py-2'><button onclick=\"navigator.clipboard.writeText('{} = {}')\" class='px-3 py-1 bg-slate-800 hover:bg-cyan-600 text-xs rounded-md text-white font-medium transition'>Copy</button></td></tr>",
            k, val_str, k, val_str
        ));
    }

    let html_content = format!(r#"
<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Physure Visualizer</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen p-8 font-sans">
    <div class="max-w-6xl mx-auto space-y-6">
        <header class="flex justify-between items-center border-b border-slate-800 pb-4">
            <div>
                <h1 class="text-3xl font-bold bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">Physure Visual Dashboard</h1>
                <p class="text-slate-400 text-sm">Interactive Physical Computation & Quantity Inspection</p>
            </div>
            <div class="flex items-center gap-3">
                <span class="px-3 py-1 bg-cyan-950 border border-cyan-800 text-cyan-400 text-xs rounded-full font-mono">v0.2.4 Live</span>
            </div>
        </header>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl flex flex-col">
                <h2 class="text-lg font-semibold text-cyan-400 mb-3 flex items-center gap-2">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"/></svg>
                    PHS Source Code
                </h2>
                <pre class="bg-slate-950 p-4 rounded-lg font-mono text-sm text-slate-300 overflow-x-auto border border-slate-800 flex-1">{}</pre>
            </div>

            <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl flex flex-col">
                <h2 class="text-lg font-semibold text-emerald-400 mb-3 flex items-center gap-2">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/></svg>
                    Quantities & Variables
                </h2>
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
    "#, code, rows_html);

    for request in server.incoming_requests() {
        let response = Response::from_string(&html_content)
            .with_header(tiny_http::Header::from_bytes(&b"Content-Type"[..], &b"text/html; charset=utf-8"[..]).unwrap());
        let _ = request.respond(response);
    }
    Ok(())
}
