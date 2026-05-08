from clir.output import echo, success, info, warning, error, debug
from clir.runtime import set_verbosity, Verbosity

set_verbosity(Verbosity(debug=True))
echo("Plain echo line.")
success("Operation completed successfully.")
info("Loaded 42 records.")
warning("Cache is stale.")
error("Connection refused.")
debug("Internal state: idle")
