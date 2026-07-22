use std::collections::HashMap;
use std::io;
use crossterm::{
    event::{self, Event, KeyCode},
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
use ratatui::{
    backend::CrosstermBackend,
    layout::{Constraint, Direction, Layout},
    style::{Color, Modifier, Style},
    widgets::{Block, Borders, Paragraph, Row, Table},
    Terminal,
};
use physure_script::value::PhsValue;
use arboard::Clipboard;

pub fn run_tui(code: &str, vars: &HashMap<String, PhsValue>) -> Result<(), Box<dyn std::error::Error>> {
    enable_raw_mode()?;
    let mut stdout = io::stdout();
    execute!(stdout, EnterAlternateScreen)?;
    let backend = CrosstermBackend::new(stdout);
    let mut terminal = Terminal::new(backend)?;

    let mut selected_idx = 0;
    let var_list: Vec<(&String, &PhsValue)> = vars.iter().collect();
    let mut status_msg = String::from("Press 'c' to copy selected variable | 'q' or Esc to exit");

    loop {
        terminal.draw(|f| {
            let chunks = Layout::default()
                .direction(Direction::Vertical)
                .constraints([
                    Constraint::Length(3),
                    Constraint::Min(10),
                    Constraint::Length(3),
                ])
                .split(f.area());

            let header = Paragraph::new("Physure TUI Dashboard v0.2.4")
                .style(Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD))
                .block(Block::default().borders(Borders::ALL).title("Physure Interactive Inspection"));
            f.render_widget(header, chunks[0]);

            let main_chunks = Layout::default()
                .direction(Direction::Horizontal)
                .constraints([Constraint::Percentage(40), Constraint::Percentage(60)])
                .split(chunks[1]);

            let code_block = Paragraph::new(code)
                .style(Style::default().fg(Color::White))
                .block(Block::default().borders(Borders::ALL).title("PHS Source Code"));
            f.render_widget(code_block, main_chunks[0]);

            let rows: Vec<Row> = var_list
                .iter()
                .enumerate()
                .map(|(i, (k, v))| {
                    let style = if i == selected_idx {
                        Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)
                    } else {
                        Style::default().fg(Color::Green)
                    };
                    Row::new(vec![k.to_string(), v.to_string()]).style(style)
                })
                .collect();

            let table = Table::new(rows, [Constraint::Percentage(40), Constraint::Percentage(60)])
                .header(Row::new(vec!["Variable", "Value"]).style(Style::default().fg(Color::Magenta)))
                .block(Block::default().borders(Borders::ALL).title("Variables & Quantities"));
            f.render_widget(table, main_chunks[1]);

            let footer = Paragraph::new(status_msg.as_str())
                .style(Style::default().fg(Color::Yellow))
                .block(Block::default().borders(Borders::ALL).title("Actions"));
            f.render_widget(footer, chunks[2]);
        })?;

        if event::poll(std::time::Duration::from_millis(100))? {
            if let Event::Key(key) = event::read()? {
                match key.code {
                    KeyCode::Char('q') | KeyCode::Esc => break,
                    KeyCode::Down => {
                        if !var_list.is_empty() {
                            selected_idx = (selected_idx + 1) % var_list.len();
                        }
                    }
                    KeyCode::Up => {
                        if !var_list.is_empty() {
                            selected_idx = if selected_idx == 0 { var_list.len() - 1 } else { selected_idx - 1 };
                        }
                    }
                    KeyCode::Char('c') => {
                        if selected_idx < var_list.len() {
                            let (k, v) = var_list[selected_idx];
                            let copy_str = format!("{} = {}", k, v);
                            if let Ok(mut cb) = Clipboard::new() {
                                if cb.set_text(copy_str.clone()).is_ok() {
                                    status_msg = format!("Copied to clipboard: {}", copy_str);
                                }
                            }
                        }
                    }
                    _ => {}
                }
            }
        }
    }

    disable_raw_mode()?;
    execute!(terminal.backend_mut(), LeaveAlternateScreen)?;
    terminal.show_cursor()?;
    Ok(())
}
