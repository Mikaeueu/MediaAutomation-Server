import { defineConfig } from "vite";

export default async () => {
  // importa dinamicamente plugins ESM-only (se você já usa esses plugins)
  let tsconfigPathsPlugin = null;
  let reactPlugin = null;

  try {
    const modTs = await import("vite-tsconfig-paths");
    const factoryTs = modTs?.default ?? modTs;
    tsconfigPathsPlugin = typeof factoryTs === "function" ? factoryTs() : null;
  } catch (e) {
    console.warn("Aviso: vite-tsconfig-paths não pôde ser importado:", e);
  }

  try {
    const modReact = await import("@vitejs/plugin-react");
    const factoryReact = modReact?.default ?? modReact;
    reactPlugin = typeof factoryReact === "function" ? factoryReact() : null;
  } catch (e) {
    console.warn("Aviso: @vitejs/plugin-react não pôde ser importado:", e);
  }

  return defineConfig({
    root: "src",                 // <-- procura index.html em frontend/src
    plugins: [
      ...(tsconfigPathsPlugin ? [tsconfigPathsPlugin] : []),
      ...(reactPlugin ? [reactPlugin] : [])
    ],
    build: {
      outDir: "../dist",         // saída final em frontend/dist (fora de src)
      emptyOutDir: true
    },
    server: {
      host: true
    }
  });
};
