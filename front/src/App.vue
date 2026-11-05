<template>
  <main>
    <p class="project-name">PORT 8282</p>
    <h1>선박 접안 스케줄링</h1>
    <p>프론트 개발 환경이 준비되었습니다.</p>
    <p class="note">대시보드와 스케줄 비교 기능을 이 화면에 구현할 예정입니다.</p>
  </main>
</template>

<style>
:root {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  color: #172a3a;
  background: #f6f8fa;
  line-height: 1.6;
}

body {
  margin: 0;
}

main {
  max-width: 800px;
  margin: 12vh auto;
  padding: 24px;
}

.project-name {
  color: #286365;
  font-weight: 700;
  letter-spacing: 0.08em;
}

h1 {
  font-size: clamp(1.75rem, 4vw, 2.5rem);
  line-height: 1.3;
}

.note {
  color: #52616e;
}
</style>
