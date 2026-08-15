import hljs from 'highlight.js/lib/common'
import { marked } from 'marked'
import 'highlight.js/styles/atom-one-dark.css'

marked.setOptions({
  gfm: true,
  breaks: true,
})

// 代码高亮：识别语言则按语言高亮，否则自动识别
const renderer = new marked.Renderer()
const originalCode = renderer.code.bind(renderer)
renderer.code = ({ text, lang }) => {
  const language = (lang ?? '').split(/\s+/)[0]
  let highlighted: string
  try {
    highlighted =
      language && hljs.getLanguage(language)
        ? hljs.highlight(text, { language }).value
        : hljs.highlightAuto(text).value
  } catch {
    highlighted = text
  }
  return `<pre><code class="hljs${language ? ` language-${language}` : ''}">${highlighted}</code></pre>`
}
marked.use({ renderer })

/** 把纯文本渲染为安全的 Markdown HTML（已做高亮）。 */
export function renderMarkdown(text: string): string {
  return marked.parse(text || '', { async: false }) as string
}
