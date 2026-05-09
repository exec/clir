from clir.output import set_theme, echo

# Each theme remaps the 5 named styles (success, info, warning, error, debug).
# Cycling through them shows how the entire palette shifts at once.
themes = ["default", "dracula", "monokai", "nord", "synthwave", "bubblegum"]

for theme in themes:
    set_theme(theme)
    echo(f"[bold]── {theme} ──[/bold]")
    echo("[success]✓ build completed in 2.3s[/success]")
    echo("[info]ℹ deploying to staging-eu-west[/info]")
    echo("[warning]⚠ disk usage at 80% on /var[/warning]")
    echo("[error]✗ connection refused on :5432[/error]")
    echo("[debug]· trace: handshake() → tls_init() → ready[/debug]")
    echo()
