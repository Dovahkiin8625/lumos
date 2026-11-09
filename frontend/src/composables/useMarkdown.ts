import { marked } from 'marked'
import hljs from 'highlight.js/lib/core'
import javascript from 'highlight.js/lib/languages/javascript'
import python from 'highlight.js/lib/languages/python'
import bash from 'highlight.js/lib/languages/bash'
import json from 'highlight.js/lib/languages/json'

// Module-level setup: register languages and configure marked exactly once.
// Anything that calls `useMarkdown()` later just gets back a tiny renderer.
hljs.registerLanguage('javascript', javascript)
hljs.registerLanguage('python', python)
hljs.registerLanguage('bash', bash)
hljs.registerLanguage('json', json)

// Marked v14 removed the built-in `highlight` option from setOptions.
// Use the official renderer override so hljs actually runs against code blocks.
marked.use({
  breaks: true,
  renderer: {
    code(token: { text: string; lang?: string } | string): string {
      const code = typeof token === 'string' ? token : token.text
      const lang = typeof token === 'string' ? undefined : token.lang
      const language = lang && hljs.getLanguage(lang) ? lang : 'plaintext'
      const highlighted =
        lang && hljs.getLanguage(lang)
          ? hljs.highlight(code, { language: lang }).value
          : hljs.highlightAuto(code).value
      return `<pre><code class="hljs language-${language}">${highlighted}</code></pre>`
    },
  },
})

/**
 * Shared markdown renderer.
 *
 * Returns a `render(src)` function that produces HTML with the same
 * syntax-highlighting configuration used in chat messages, so a skill
 * instructions preview matches what users actually see at runtime.
 *
 * Empty / whitespace-only input returns an empty string so callers can
 * cheaply `v-if` on the result.
 */
export function useMarkdown() {
  function render(src: string | undefined | null): string {
    if (!src || !src.trim()) return ''
    try {
      return marked.parse(src) as string
    } catch {
      return ''
    }
  }
  return { render }
}