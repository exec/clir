from clir.output import Table

t = Table("Component", "Status", "Latency")
t.add_row("API", "[green]running[/green]", "12ms")
t.add_row("Database", "[green]running[/green]", "3ms")
t.add_row("Cache", "[yellow]degraded[/yellow]", "84ms")
t.add_row("Queue", "[red]down[/red]", "—")
t.show()
