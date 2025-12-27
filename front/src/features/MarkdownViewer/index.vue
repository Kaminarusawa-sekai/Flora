<script setup lang="ts">
import { ref, onMounted } from 'vue';
import MarkdownIt from 'markdown-it';
import DOMPurify from 'dompurify';

const markdownContent = ref('');
const renderedHtml = ref('');

// 创建 markdown-it 实例
const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true,
  breaks: true
});

// 加载并渲染 markdown 文件
onMounted(async () => {
  try {
    // 使用 fetch 加载本地 markdown 文件
    const response = await fetch('/src/assets/docs/flora.md');
    if (!response.ok) {
      throw new Error(`Failed to load markdown file: ${response.statusText}`);
    }
    
    markdownContent.value = await response.text();
    
    // 渲染 markdown 为 HTML
    const rawHtml = md.render(markdownContent.value);
    
    // 净化 HTML 以防止 XSS
    renderedHtml.value = DOMPurify.sanitize(rawHtml);
  } catch (error) {
    console.error('Error loading or rendering markdown:', error);
    renderedHtml.value = `<div class="text-red-500">Error loading documentation: ${(error as Error).message}</div>`;
  }
});
</script>

<template>
  <div class="markdown-viewer h-full overflow-y-auto p-8">
    <div class="max-w-4xl mx-auto" v-html="renderedHtml"></div>
  </div>
</template>

<style scoped>
.markdown-viewer {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.02) 100%);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

/* 基础 markdown 样式 */
:deep(h1) {
  font-size: 2.5rem;
  font-weight: 700;
  margin-bottom: 1rem;
  color: #ffffff;
  text-align: center;
  background: linear-gradient(135deg, #4F46E5 0%, #8B5CF6 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

:deep(h2) {
  font-size: 2rem;
  font-weight: 600;
  margin: 2rem 0 1rem;
  color: #e0e7ff;
  border-bottom: 2px solid rgba(79, 70, 229, 0.3);
  padding-bottom: 0.5rem;
}

:deep(h3) {
  font-size: 1.5rem;
  font-weight: 600;
  margin: 1.5rem 0 0.75rem;
  color: #c7d2fe;
}

:deep(p) {
  margin-bottom: 1rem;
  line-height: 1.6;
  color: #d1d5db;
}

:deep(a) {
  color: #60a5fa;
  text-decoration: none;
  transition: all 0.3s ease;
}

:deep(a:hover) {
  color: #3b82f6;
  text-decoration: underline;
}

:deep(ul), :deep(ol) {
  margin: 1rem 0;
  padding-left: 1.5rem;
  color: #d1d5db;
}

:deep(li) {
  margin-bottom: 0.5rem;
  line-height: 1.6;
}

:deep(li > ul), :deep(li > ol) {
  margin: 0.5rem 0 0;
}

:deep(code) {
  background-color: rgba(79, 70, 229, 0.15);
  color: #a5b4fc;
  padding: 0.2rem 0.4rem;
  border-radius: 4px;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 0.9em;
}

:deep(pre) {
  background-color: rgba(17, 24, 39, 0.8);
  border: 1px solid rgba(79, 70, 229, 0.2);
  border-radius: 8px;
  padding: 1rem;
  overflow-x: auto;
  margin: 1rem 0;
}

:deep(pre code) {
  background: none;
  padding: 0;
  color: #e0e7ff;
}

:deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 1rem 0;
}

:deep(th), :deep(td) {
  padding: 0.75rem;
  text-align: left;
  border: 1px solid rgba(79, 70, 229, 0.2);
  color: #d1d5db;
}

:deep(th) {
  background-color: rgba(79, 70, 229, 0.1);
  font-weight: 600;
  color: #c7d2fe;
}

:deep(tr:nth-child(even)) {
  background-color: rgba(79, 70, 229, 0.05);
}

:deep(blockquote) {
  border-left: 4px solid #4F46E5;
  padding: 0.5rem 1rem;
  margin: 1rem 0;
  background-color: rgba(79, 70, 229, 0.05);
  color: #d1d5db;
}

:deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  margin: 1rem 0;
  border: 1px solid rgba(79, 70, 229, 0.2);
}

:deep(hr) {
  border: none;
  border-top: 1px solid rgba(79, 70, 229, 0.2);
  margin: 2rem 0;
}
</style>