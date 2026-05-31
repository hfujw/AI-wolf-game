import { useEffect, useRef } from 'react';

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  opacity: number;
  life: number;
  maxLife: number;
}

export default function BackgroundParticles() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let w = window.innerWidth;
    let h = window.innerHeight;
    canvas.width = w;
    canvas.height = h;

    const particles: Particle[] = [];
    const maxParticles = 60;

    function spawnParticle(): Particle {
      return {
        x: Math.random() * w,
        y: Math.random() * h,
        vx: (Math.random() - 0.5) * 0.3,
        vy: -(Math.random() * 0.5 + 0.1),
        size: Math.random() * 2 + 0.5,
        opacity: Math.random() * 0.4 + 0.1,
        life: 0,
        maxLife: Math.random() * 300 + 200,
      };
    }

    for (let i = 0; i < maxParticles; i++) {
      const p = spawnParticle();
      p.life = Math.random() * p.maxLife;
      particles.push(p);
    }

    let animId: number;

    function draw() {
      ctx?.clearRect(0, 0, w, h);

      for (let i = particles.length - 1; i >= 0; i--) {
        const p = particles[i];
        p.x += p.vx;
        p.y += p.vy;
        p.life += 1;

        if (p.life > p.maxLife || p.y < -10 || p.x < -10 || p.x > w + 10) {
          particles.splice(i, 1, spawnParticle());
          continue;
        }

        const alpha = p.opacity * (1 - p.life / p.maxLife);
        ctx?.beginPath();
        ctx?.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        if (ctx) ctx.fillStyle = `rgba(180, 200, 255, ${alpha})`;
        ctx?.fill();
      }

      while (particles.length < maxParticles) {
        particles.push(spawnParticle());
      }

      animId = requestAnimationFrame(draw);
    }

    const handleResize = () => {
      w = window.innerWidth;
      h = window.innerHeight;
      canvas.width = w;
      canvas.height = h;
    };

    window.addEventListener('resize', handleResize);
    draw();

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  return <canvas ref={canvasRef} className="particles-bg" />;
}
