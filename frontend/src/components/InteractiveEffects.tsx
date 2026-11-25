import { useEffect, useRef } from 'react';

export function InteractiveEffects() {
  const cursorRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const cursor = cursorRef.current;
    const finePointer = window.matchMedia('(pointer: fine)');
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    if (!cursor || !finePointer.matches || reducedMotion.matches) return;

    const root = document.documentElement;
    let frame = 0;
    let pointerX = 0;
    let pointerY = 0;
    root.classList.add('has-custom-cursor');

    const updatePointer = (event: PointerEvent) => {
      if (event.pointerType === 'touch') return;
      pointerX = event.clientX;
      pointerY = event.clientY;
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        cursor.style.transform = `translate3d(${pointerX}px, ${pointerY}px, 0)`;
        root.classList.add('cursor-active');
      });
    };

    const updateHover = (event: PointerEvent) => {
      const target = event.target;
      const interactive =
        target instanceof Element &&
        target.closest('a, button, [role="button"], [data-cursor-hover]') !== null;
      root.classList.toggle('cursor-hover', interactive);
    };

    const deactivate = () => {
      root.classList.remove('cursor-active', 'cursor-hover', 'cursor-pressed');
    };

    const handlePointerDown = () => root.classList.add('cursor-pressed');
    const handlePointerUp = () => root.classList.remove('cursor-pressed');

    window.addEventListener('pointermove', updatePointer, { passive: true });
    window.addEventListener('pointerover', updateHover, { passive: true });
    window.addEventListener('pointerdown', handlePointerDown, { passive: true });
    window.addEventListener('pointerup', handlePointerUp, { passive: true });
    window.addEventListener('blur', deactivate);
    document.addEventListener('pointerleave', deactivate);

    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener('pointermove', updatePointer);
      window.removeEventListener('pointerover', updateHover);
      window.removeEventListener('pointerdown', handlePointerDown);
      window.removeEventListener('pointerup', handlePointerUp);
      window.removeEventListener('blur', deactivate);
      document.removeEventListener('pointerleave', deactivate);
      root.classList.remove('has-custom-cursor', 'cursor-active', 'cursor-hover', 'cursor-pressed');
    };
  }, []);

  return (
    <div className="custom-cursor" ref={cursorRef} aria-hidden="true">
      <span className="custom-cursor__glow" />
      <svg className="custom-cursor__arrow" viewBox="0 0 28 34" focusable="false">
        <path
          d="M2.5 1.5v27l7.2-7.1 4.7 10.1 4.3-2-4.7-10.1 10.6-.4L2.5 1.5Z"
          fill="#d9d4e7"
          stroke="#0b1713"
          strokeLinejoin="round"
          strokeWidth="2"
        />
      </svg>
    </div>
  );
}
