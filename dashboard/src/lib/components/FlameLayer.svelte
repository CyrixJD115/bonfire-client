<script lang="ts">
  interface Particle {
    left: number;
    duration: number;
    delay: number;
    size: number;
  }

  let particles = $state<Particle[]>([]);

  function init() {
    const count = 16;
    particles = Array.from({ length: count }, () => ({
      left: Math.random() * 100,
      duration: 3 + Math.random() * 4,
      delay: Math.random() * 5,
      size: 2 + Math.random() * 2,
    }));
  }

  init();
</script>

<div class="absolute inset-0 pointer-events-none overflow-hidden">
  {#each particles as p}
    <div
      class="absolute bottom-0 rounded-full bg-amber-400/60"
      style="left: {p.left}%; width: {p.size}px; height: {p.size}px;
             animation: ember-rise {p.duration}s linear infinite;
             animation-delay: {p.delay}s;
             box-shadow: 0 0 6px rgba(245,158,11,0.6);"
    ></div>
  {/each}
</div>
