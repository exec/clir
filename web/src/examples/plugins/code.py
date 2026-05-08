from clir import ClirApp
from clir.plugins import PluginManager, Plugin

app = ClirApp(name="myapp")
pm = PluginManager(app)


# Register a plugin in code (the real plugin system also discovers
# entry-point packages and on-disk plugin files via load_from_directory).
class HelloPlugin(Plugin):
    name = "hello"
    version = "1.0.0"

    def on_register(self):
        @self.app.command(name="hello")
        def hello_cmd():
            """Hello from a plugin."""
            print("Hello from a plugin!")


pm.register(HelloPlugin)
print("Plugins registered:", pm.list())
app.run(["hello"])
