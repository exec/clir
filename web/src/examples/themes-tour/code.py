from clir.output import set_theme, get_console, success, Panel

for theme in ["default", "dracula", "monokai", "nord"]:
    set_theme(theme)
    success(f"--- {theme} ---")
    Panel("Hello from " + theme, title=theme).show()
