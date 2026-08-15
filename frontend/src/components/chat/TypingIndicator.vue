<template>
  <div class="typing" role="status" aria-label="正在生成">
    <span class="typing-dots"><span /><span /><span /></span>
    <span class="typing-text">知知正在思考…</span>
  </div>
</template>

<style scoped>
.typing {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 10px 2px;
}
.typing-text {
  font-size: 13px;
  color: var(--text-3);
}
</style>
