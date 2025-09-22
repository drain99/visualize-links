import { defineConfig } from 'vite'
import { viteSingleFile } from 'vite-plugin-singlefile'

export default defineConfig({
  plugins: [
    viteSingleFile({deleteInlinedFiles: true}),
  ],
  build: {
    assetsInlineLimit: 100000000,
    cssCodeSplit: false,
  }
})
