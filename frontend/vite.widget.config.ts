import { defineConfig } from "vite";

// Separate build target: the embeddable widget is framework-free (no React)
// so it stays a tiny, dependency-free bundle any third-party site can load
// with a single <script> tag. Output goes to public/widget/ so both `vite`
// (dev server) and `vite build` (which copies public/ into dist/) serve it
// at the same /widget/ekip-widget.js path with zero extra wiring.
export default defineConfig({
  build: {
    outDir: "public/widget",
    emptyOutDir: false,
    lib: {
      entry: "src/widget/embed.ts",
      formats: ["iife"],
      name: "EKIPWidget",
      fileName: () => "ekip-widget.js",
    },
    minify: true,
  },
});
