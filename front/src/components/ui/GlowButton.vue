<template>
  <button
    :disabled="disabled || loading"
    class="
      group relative flex items-center justify-center
      font-medium tracking-wide transition-all duration-300 ease-out
      backdrop-blur-sm overflow-hidden
      disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none disabled:border-white/10 disabled:bg-white/5
    "
    :class="[
      sizeClasses[size], 
      variantClasses[variant],
      // 统一圆角，这里使用 xl 配合整个系统的圆润度，或者用 lg 也可以
      'rounded-xl' 
    ]"
  >
    <div
      class="absolute inset-0 opacity-0 transition-opacity duration-500 blur-xl group-hover:opacity-40"
      :class="glowColors[variant]"
    ></div>

    <div class="absolute inset-0 -translate-x-full group-hover:animate-[shimmer_1.5s_infinite] bg-gradient-to-r from-transparent via-white/10 to-transparent z-0"></div>

    <span class="relative z-10 flex items-center gap-2">
      <svg v-if="loading" class="animate-spin w-4 h-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
      <slot v-else></slot>
    </span>
  </button>
</template>

<script setup lang="ts">
type Variant = 'primary' | 'danger' | 'success' | 'ghost';
type Size = 'sm' | 'md' | 'lg';

const props = defineProps({
  variant: { type: String as () => Variant, default: 'primary' },
  size: { type: String as () => Size, default: 'md' },
  loading: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false }
});

// 尺寸配置
const sizeClasses = {
  sm: 'px-3 py-1.5 text-xs',
  md: 'px-5 py-2.5 text-sm',
  lg: 'px-8 py-3 text-base'
};

// 风格配置 (适配新的 Theme)
// 核心逻辑：背景变淡 (/10 ~ /20)，边框变亮，利用 shadow-glow 制造氛围
const variantClasses = {
  // Primary: 青色主调，呼应系统光效
  primary: `
    bg-cyan-500/10 text-cyan-50 border border-cyan-500/50 
    hover:bg-cyan-500/20 hover:border-cyan-400 hover:text-white
    shadow-[0_0_20px_rgba(6,182,212,0.15)] hover:shadow-glow-cyan hover:-translate-y-[1px]
  `,
  
  // Danger: 红色警示
  danger: `
    bg-red-500/10 text-red-50 border border-red-500/50 
    hover:bg-red-500/20 hover:border-red-400 hover:text-white
    shadow-[0_0_20px_rgba(239,68,68,0.15)] hover:shadow-glow-red hover:-translate-y-[1px]
  `,
  
  // Success: 绿色完成
  success: `
    bg-emerald-500/10 text-emerald-50 border border-emerald-500/50 
    hover:bg-emerald-500/20 hover:border-emerald-400 hover:text-white
    shadow-[0_0_20px_rgba(16,185,129,0.15)] hover:shadow-glow-green hover:-translate-y-[1px]
  `,
  
  // Ghost: 幽灵按钮，平时几乎隐形，Hover时显现
  ghost: `
    bg-transparent text-gray-400 border border-transparent 
    hover:bg-white/5 hover:text-cyan-300 hover:border-white/10
  `
};

// 底部模糊光晕颜色 (背景流光)
const glowColors = {
  primary: 'bg-gradient-to-r from-cyan-400 to-blue-600',
  danger: 'bg-gradient-to-r from-red-500 to-orange-600',
  success: 'bg-gradient-to-r from-emerald-400 to-green-600',
  ghost: 'bg-white'
};
</script>

<style scoped>
/* 定义一个微弱的扫光动画 */
@keyframes shimmer {
  100% { transform: translateX(100%); }
}
</style>