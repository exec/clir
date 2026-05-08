import { defineConfig } from "astro/config";
import tailwind from "@astrojs/tailwind";
import preact from "@astrojs/preact";

export default defineConfig({
  site: "https://clir.byexec.com",
  integrations: [tailwind(), preact()],
  output: "static",
  build: {
    assets: "assets",
  },
});
